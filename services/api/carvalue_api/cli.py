"""Command-line entry point for the CarValue modular monolith (M0).

Wires together database initialization, server startup, and seed data. The
worker/scheduler lives in ``services/worker`` and is a separate process; this
CLI only manages the API side of things.
"""

from __future__ import annotations

import argparse
import secrets
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from carvalue_core.persistence import (
    AdminUser,
    VehicleTaxonomy,
    new_session_factory,
)
from sqlalchemy import select

import carvalue_api as api


def _bcrypt(token: str) -> str:  # minimal stand-in; swap for bcrypt in M5
    import hashlib

    return hashlib.sha256(f"m0-dev-only:{token}".encode()).hexdigest()


def _seed_db(session: Any, *, db_path: str | Path) -> None:
    """Seed the taxonomy system of record and a default admin (first-boot)."""
    from carvalue_core.taxonomy import seed_pickup_taxonomy

    existing_ids = session.execute(select(VehicleTaxonomy.id)).scalars().all()
    if not existing_ids:
        parent_ids: dict[str, int] = {}
        for node in seed_pickup_taxonomy():
            if node.level == "make":
                row = VehicleTaxonomy(
                    level="make",
                    canonical_name=node.canonical_name,
                    aliases_json=list(node.aliases),
                )
                session.add(row)
                session.flush()
                parent_ids[node.canonical_name] = int(row.id)  # type: ignore[arg-type]
        for node in seed_pickup_taxonomy():
            if node.level == "model":
                parent_id = parent_ids.get(node.parent_canonical) if node.parent_canonical else None
                row = VehicleTaxonomy(
                    level="model",
                    canonical_name=node.canonical_name,
                    aliases_json=list(node.aliases),
                    parent_id=parent_id,
                )
                session.add(row)
                session.flush()
                parent_ids[node.canonical_name] = int(row.id)  # type: ignore[arg-type]
        for node in seed_pickup_taxonomy():
            if node.level == "trim":
                parent_id = parent_ids.get(node.parent_canonical) if node.parent_canonical else None
                row = VehicleTaxonomy(
                    level="trim",
                    canonical_name=node.canonical_name,
                    aliases_json=list(node.aliases),
                    parent_id=parent_id,
                )
                session.add(row)

    admin_count = session.execute(select(AdminUser.id)).scalars().all()
    if not admin_count:
        salt = secrets.token_hex(16)
        token = secrets.token_hex(32)
        pw_hash = f"$2b$12${salt}${_bcrypt(token)}"
        session.add(
            AdminUser(
                email="admin@carvalue.local",
                password_hash=pw_hash,
                display_name="CarValue Administrator",
                is_active=True,
                created_at=datetime.now(UTC),
            )
        )


def do_init_db(db_url: str = "sqlite:///./carvalue.db") -> None:
    """Create tables (if missing), seed taxonomy + admin, record schema hash."""
    Path(db_path_from_url(db_url)).touch(exist_ok=True)
    from carvalue_api.migrations import run_migrations

    marker = run_migrations(db_url=db_url, target_dir=str(Path(db_path_from_url(db_url)).parent))
    SessionLocal = new_session_factory(api.persistence.make_engine(db_url))
    with SessionLocal() as session:  # type: ignore[union-attr]
        _seed_db(session, db_path=db_url)
        session.commit()
    engine = api.persistence.make_engine(db_url)
    engine.dispose()
    print("database initialized:", marker["schema_hash"], f"({len(marker['tables'])} tables)")


def do_run_server(host: str = "127.0.0.1", port: int = 8000, db_url: str | None = None) -> None:
    import uvicorn

    if db_url is not None:
        api.app.state.db_url = db_url
    config = uvicorn.Config(app=api.app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config=config)
    server.run()


def db_path_from_url(db_url: str) -> str:
    """Extract the filesystem path from a ``sqlite:///`` URL."""
    prefix = "sqlite:///"
    return db_url[len(prefix) :] if db_url.startswith(prefix) else "carvalue.db"


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="carvalue", description="CarValue modular monolith CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init-db",
        help="initialize SQLite with migrations + seed data",
    )
    init_parser.add_argument("--db-url", default="sqlite:///./carvalue.db")
    init_parser.set_defaults(func=lambda a: do_init_db(db_url=a.db_url))

    run_parser = subparsers.add_parser("run", help="start the FastAPI server")
    run_parser.add_argument("--host", default="127.0.0.1")
    run_parser.add_argument("--port", type=int, default=8000)
    run_parser.add_argument("--db-url", default=None)
    run_parser.set_defaults(func=lambda a: do_run_server(host=a.host, port=a.port, db_url=a.db_url))

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
