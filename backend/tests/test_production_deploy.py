"""Audit G-11: the production stack's guarantees that can be checked without Docker.

The compose and nginx files are read as text (no YAML dependency in the backend). The tests skip when the repo
files aren't visible (e.g. inside the backend image, which has only backend/ and its siblings)."""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _read(rel):
    path = ROOT / rel
    if not path.exists():
        pytest.skip(f"{rel} not visible here")
    return path.read_text(encoding="utf-8")


def _service_blocks(compose: str) -> dict:
    """{service name: its text} for the top-level `services:` section."""
    section = compose.split("\nservices:\n", 1)[1].split("\nvolumes:\n", 1)[0]
    blocks, name = {}, None
    for line in section.splitlines():
        m = re.match(r"^  ([a-z][\w-]*):\s*$", line)
        if m:
            name = m.group(1)
            blocks[name] = ""
        elif name:
            blocks[name] += line + "\n"
    return blocks


# ── API docs ──────────────────────────────────────────────────────────────────

def test_docs_are_off_outside_dev(monkeypatch):
    import main
    monkeypatch.setenv("APP_ENV", "production")
    assert main._api_docs_settings() == {"docs_url": None, "redoc_url": None, "openapi_url": None}
    monkeypatch.delenv("APP_ENV")
    assert main._api_docs_settings()["openapi_url"] is None


def test_docs_are_on_in_dev(monkeypatch):
    import main
    monkeypatch.setenv("APP_ENV", "dev")
    assert main._api_docs_settings() == {}


# ── Production compose ────────────────────────────────────────────────────────

def test_only_nginx_is_published():
    services = _service_blocks(_read("docker-compose.prod.yml"))
    assert {"mongodb", "backend", "ml", "frontend"} <= set(services)
    published = {name for name, text in services.items() if re.search(r"^    ports:", text, re.M)}
    assert published == {"frontend"}


def test_mongo_requires_auth_and_the_app_uses_its_own_user():
    services = _service_blocks(_read("docker-compose.prod.yml"))
    mongo, backend = services["mongodb"], services["backend"]
    assert "MONGO_INITDB_ROOT_PASSWORD: ${MONGO_ROOT_PASSWORD:?" in mongo
    assert "MONGO_APP_PASSWORD: ${MONGO_APP_PASSWORD:?" in mongo
    assert "./deploy/mongo-init:/docker-entrypoint-initdb.d:ro" in mongo
    uri = re.search(r"MONGO_URI: (.+)", backend).group(1)
    assert "${MONGO_APP_USER" in uri and "${MONGO_APP_PASSWORD}" in uri and "MONGO_ROOT" not in uri


def test_backend_runs_as_production_without_bind_mounts():
    backend = _service_blocks(_read("docker-compose.prod.yml"))["backend"]
    assert "APP_ENV: production" in backend
    assert "JWT_SECRET: ${JWT_SECRET:?" in backend
    assert 'TRUST_PROXY_HEADERS: "true"' in backend
    assert ":/app/" not in backend          # the built image, not the working tree
    assert "command:" not in backend        # the Dockerfile's CMD (with --proxy-headers)


def test_every_service_rotates_logs_and_ml_is_not_root():
    services = _service_blocks(_read("docker-compose.prod.yml"))
    for name, text in services.items():
        assert "logging: *logging" in text, name
    for name in ("ml", "ml-refresh", "ml-nft-refresh"):
        assert 'user: "10001:10001"' in services[name], name


def test_compose_files_have_no_obsolete_version_key():
    for rel in ("docker-compose.yml", "docker-compose.prod.yml"):
        assert not re.search(r"^version:", _read(rel), re.M), rel


# ── Images ────────────────────────────────────────────────────────────────────

def test_backend_image_is_not_root():
    dockerfile = _read("backend/Dockerfile")
    assert dockerfile.splitlines()[0].startswith("# syntax=")
    assert re.search(r"^USER app$", dockerfile, re.M)
    assert "--proxy-headers" in dockerfile


def test_frontend_images_use_the_lockfile():
    for rel in ("frontend/Dockerfile", "frontend/Dockerfile.prod"):
        text = _read(rel)
        assert "npm ci" in text and "npm install" not in text, rel
    assert "node_modules" in _read("frontend/.dockerignore")


def test_frontend_image_defaults_to_the_same_origin_proxy():
    prod = _read("frontend/Dockerfile.prod")
    assert "ARG VITE_API_BASE_URL=/api" in prod
    assert "localhost" not in prod
    assert "nginx-unprivileged" in prod


# ── nginx ─────────────────────────────────────────────────────────────────────

def test_nginx_proxies_api_without_trusting_client_forwarded_for():
    conf = _read("frontend/nginx.conf")
    assert "location /api/" in conf
    assert "rewrite ^/api/(.*)$ /$1 break;" in conf
    assert "proxy_set_header X-Forwarded-For $remote_addr;" in conf
    assert "$proxy_add_x_forwarded_for" not in conf


def test_every_nginx_location_sends_the_security_headers():
    conf = _read("frontend/nginx.conf")
    # healthz returns early and needs none; every other location adds its own headers, so must include them all.
    blocks = re.findall(r"location ([^{]+)\{(.*?)\n    \}", conf, re.S)
    assert len(blocks) >= 4
    for where, body in blocks:
        if where.strip() == "= /healthz":
            continue
        assert "include /etc/nginx/snippets/security-headers.conf;" in body, where


def test_security_headers():
    headers = _read("frontend/nginx-security-headers.conf")
    csp = re.search(r'Content-Security-Policy "([^"]+)"', headers).group(1)
    directives = dict(d.strip().split(" ", 1) for d in csp.split(";") if " " in d.strip())
    assert "'unsafe-inline'" not in directives["script-src"]
    assert "'unsafe-eval'" not in directives["script-src"]
    assert directives["frame-ancestors"] == "'none'"
    assert directives["object-src"] == "'none'"
    for name in ("X-Content-Type-Options", "Referrer-Policy", "Strict-Transport-Security", "X-Frame-Options"):
        assert name in headers
