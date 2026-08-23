"""M0 exit-gate: migrations create a fresh SQLite database from Base."""
import sqlite3

from carvalue_core.persistence import make_engine, new_session_factory
from sqlalchemy import text


def test_migrations_create_fresh_database(tmp_path) -> None:
    """A brand-new db file must gain every table after run_migrations()."""
    db = tmp_path / "fresh.db"
    assert not db.exists(), "test isolation: db should be empty"

    from carvalue_api.migrations import run_migrations

    run_migrations(db_url=f"sqlite:///{db}")

    con = sqlite3.connect(str(db))
    tables = {
        row[0]
        for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    con.close()

    expected = {
        "sources",
        "crawl_schedules",
        "crawl_runs",
        "raw_observations",
        "listings",
        "listing_price_history",
        "vehicle_taxonomy",
        "data_quality_issues",
        "dataset_snapshots",
        "model_versions",
        "valuation_events",
        "admin_users",
        "admin_sessions",
        "audit_events",
    }
    missing = expected - tables
    assert not missing, f"tables created by migration missing: {sorted(missing)}"


def test_migrations_are_idempotent(tmp_path) -> None:
    """Running migrations twice must not raise (re-run safe)."""
    db = tmp_path / "twice.db"
    from carvalue_api.migrations import run_migrations

    run_migrations(db_url=f"sqlite:///{db}")
    run_migrations(db_url=f"sqlite:///{db}")  # second run must be a no-op, not an error


def test_migration_creates_wal_and_foreign_keys(tmp_path) -> None:
    """SQLite conventions (AGENTS.md): WAL mode + foreign keys enabled.

    ``journal_mode`` is persisted in the file header, so a raw connection can
    read it. ``foreign_keys`` is per-connection and not persisted, so we verify
    it on the SA-managed connection where the pragma listener actually applies.
    """
    db = tmp_path / "conventions.db"
    from carvalue_api.migrations import run_migrations

    run_migrations(db_url=f"sqlite:///{db}")

    # Persisted journal mode (WAL survives as the file's default).
    con = sqlite3.connect(str(db))
    journal = con.execute("PRAGMA journal_mode").fetchone()[0]
    con.close()
    assert str(journal).upper() == "WAL", f"journal mode was {journal}"

    # foreign_keys on the SA-managed connection (listener applies there).
    engine = make_engine(f"sqlite:///{db}")
    SessionLocal = new_session_factory(engine)
    with SessionLocal() as session:  # type: ignore[union-attr]
        fkeys = session.execute(text("PRAGMA foreign_keys")).fetchone()[0]
    engine.dispose()
    assert fkeys == 1, f"foreign keys were OFF ({fkeys})"
