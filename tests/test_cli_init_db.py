"""M0: the ``carvalue init-db`` entry point seeds a fresh database."""

import sqlite3


def test_cli_init_db_seeds_taxonomy_and_admin(tmp_path) -> None:
    """Running the CLI init-db must create tables, seed taxonomy, and one admin."""
    db = tmp_path / "cli.db"
    url = f"sqlite:///{db}"

    from carvalue_api.cli import do_init_db

    do_init_db(db_url=url)

    con = sqlite3.connect(str(db))
    tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    admin_rows = con.execute("SELECT COUNT(*) FROM admin_users").fetchone()[0]
    taxonomy_rows = con.execute("SELECT COUNT(*) FROM vehicle_taxonomy").fetchone()[0]
    con.close()

    assert "admin_users" in tables and "vehicle_taxonomy" in tables
    assert admin_rows >= 1, "no default admin seeded on first boot"
    assert taxonomy_rows >= 6, "taxonomy system of record not seeded (>=3 makes + 2 models + trims)"


def test_cli_init_db_is_repeatable(tmp_path) -> None:
    """Re-running init-db must not duplicate the admin or raise."""
    db = tmp_path / "cli_twice.db"
    url = f"sqlite:///{db}"

    from carvalue_api.cli import do_init_db

    do_init_db(db_url=url)
    do_init_db(db_url=url)  # second boot: idempotent, no duplicate admin

    con = sqlite3.connect(str(db))
    admin_rows = con.execute("SELECT COUNT(*) FROM admin_users").fetchone()[0]
    con.close()
    assert admin_rows == 1, f"admin duplicated on re-boot ({admin_rows})"
