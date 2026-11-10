"""
db/seed_guard.py
Seeds write demo data, so they run only against a local MongoDB unless asked otherwise
(ml/docs/DECISIONS.md D69, Phase 10 step 10.5b).

Local means localhost, 127.0.0.1, ::1, or `mongodb` (the docker-compose service, the altinvest-mongo
container). Any other host, and every mongodb+srv:// URI (Atlas), is refused unless the command line has
--allow-remote. The URI is read the same way db/mongo_connection.py reads it (MONGO_URI, after backend/.env);
an unset URI means pymongo's default, localhost. Only hosts are ever printed, never credentials.
"""
import os
import sys

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "mongodb"}
ALLOW_FLAG = "--allow-remote"


def uri_hosts(uri: str | None) -> tuple[str, list[str]]:
    """(scheme, hosts) of a MongoDB URI, credentials and options dropped."""
    if not uri:
        return "mongodb", ["localhost"]
    scheme, _, rest = uri.partition("://")
    hostpart = rest.split("/", 1)[0].split("?", 1)[0].rsplit("@", 1)[-1]
    hosts = []
    for h in hostpart.split(","):
        h = h.strip()
        if h.startswith("["):                                   # [::1]:27017
            hosts.append(h[1:h.index("]")])
        else:
            hosts.append(h.split(":", 1)[0])
    return scheme, [h.lower() for h in hosts if h]


def is_local(uri: str | None) -> bool:
    scheme, hosts = uri_hosts(uri)
    return scheme == "mongodb" and bool(hosts) and all(h in LOCAL_HOSTS for h in hosts)


def require_local_target(argv=None, uri: str | None = None) -> None:
    """Exit with a message unless the seed target is local or --allow-remote was given."""
    argv = sys.argv if argv is None else argv
    if uri is None:
        import db.mongo_connection  # noqa: F401  (loads backend/.env exactly as the seeds' connection does)
        uri = os.getenv("MONGO_URI")
    if is_local(uri) or ALLOW_FLAG in argv:
        return
    scheme, hosts = uri_hosts(uri)
    sys.exit(f"refusing to seed a non-local MongoDB ({scheme}://{','.join(hosts)}); seeds write demo data. "
             f"Point MONGO_URI at the local container, or pass {ALLOW_FLAG} to seed this database on purpose.")
