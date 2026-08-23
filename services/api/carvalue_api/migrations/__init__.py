"""Alembic-style migrations for the CarValue SQLite database (M0).

The MVP uses a single-host SQLite. Every schema change flows through this entry
point so that a fresh database and an existing one both converge on the same
tables declared by ``carvalue_core.persistence.Base``. This is deliberately not
a full Alembic install yet; it applies Base metadata via ``create_all`` and
records a migration marker for reproducibility (AGENTS.md: migrations for every
schema change).
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from carvalue_core.persistence import SQLITE_BUSY_TIMEOUT_MS, Base
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.event import listens_for


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _attach_pragmas(engine: Engine) -> None:
    """WAL mode, foreign keys, busy timeout (AGENTS.md persistence conventions)."""

    @listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection: Any, record: Any) -> None:  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS};")
            cursor.execute("PRAGMA foreign_keys=ON;")
        finally:
            cursor.close()


def _schema_hash(engine: Engine) -> str:
    """Stable hash of the applied schema (reproducibility marker)."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name")
        ).fetchall()
    blob = "\n".join(f"{r[0]}:{r[1]}" for r in rows)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def run_migrations(
    db_url: str = "sqlite:///./carvalue.db",
    *,
    target_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Apply Base metadata to a database and record the applied schema hash.

    Idempotent: re-running against an existing database is a no-op that still
    returns the current schema hash (M0 exit gate). Returns the applied schema
    hash so callers can verify reproducibility.
    """
    engine = create_engine(db_url, future=True)
    if db_url.startswith("sqlite"):
        _attach_pragmas(engine)

    Base.metadata.create_all(engine)  # creates missing tables; no-ops existing ones
    schema_hash = _schema_hash(engine)
    engine.dispose()

    marker: dict[str, Any] = {
        "applied_at_utc": _utcnow().isoformat(),
        "schema_hash": schema_hash,
        "tables": sorted(Base.metadata.tables.keys()),
    }
    if target_dir is not None:
        Path(target_dir).mkdir(parents=True, exist_ok=True)
        (Path(target_dir) / "migration.marker.json").write_text(
            str(marker), encoding="utf-8"
        )
    return marker
