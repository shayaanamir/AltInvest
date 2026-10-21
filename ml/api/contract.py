"""The response schemas, parsed from docs/CONTRACT.md: the single source, never copied (AGENTS rule 14)."""

import json
import re
from pathlib import Path

from jsonschema import Draft7Validator

CONTRACT_MD = Path(__file__).resolve().parent.parent / "docs" / "CONTRACT.md"
_JSON_BLOCK = re.compile(r"```json\s*\n(.*?)```", re.S)


class ContractViolation(ValueError):
    """A response body does not validate against its CONTRACT.md schema."""


def load_schemas(path: Path = CONTRACT_MD) -> dict[str, dict]:
    """{title: schema} for every JSON block in CONTRACT.md that declares a $schema (examples are skipped)."""
    blocks = [json.loads(b) for b in _JSON_BLOCK.findall(path.read_text(encoding="utf-8"))]
    return {b["title"]: b for b in blocks if "$schema" in b}


def validator(schema: dict) -> Draft7Validator:
    """Draft-07 validator that also checks formats such as date-time."""
    Draft7Validator.check_schema(schema)
    return Draft7Validator(schema, format_checker=Draft7Validator.FORMAT_CHECKER)


VALIDATORS = {title: validator(s) for title, s in load_schemas().items()}


def check(title: str, body: dict) -> dict:
    """Return body unchanged if it validates against schema `title`; raise ContractViolation otherwise."""
    errors = sorted(VALIDATORS[title].iter_errors(body), key=lambda e: list(e.path))
    if errors:
        raise ContractViolation(f"{title}: " + "; ".join(f"{list(e.path)}: {e.message}" for e in errors))
    return body
