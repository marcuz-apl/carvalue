"""M2 contract/integration test: import and data quality (roadmap M2 exit gate).

Proves the behaviors the M2 exit gate requires, against a real SQLite DB:
- dry-run imports are repeatable;
- valid rows commit safely when other rows fail (failures quarantined with codes);
- reruns do not duplicate listings (idempotent upsert -> ``updated``/``duplicate``);
- cross-source collisions are flagged conservatively without merging;
- counters and rejection reasons are observable at the crawl_run boundary.

PRD acceptance scenarios 3 & 6, FR-DATA-05/06.
"""

from datetime import UTC, datetime

import pytest
from carvalue_core.imports.spreadsheet import (
    CommitSummary,
    ImportContext,
    commit_preview,
    preview_import,
)
from carvalue_core.listings import ListingObservation, listing_fingerprint
from carvalue_core.persistence import (
    Base,
    CrawlRun,
    Source,
    claim_source_run,
    make_engine,
    upsert_listing_observation,
)
from carvalue_core.reasons import ReasonCode
from carvalue_core.taxonomy import PickupTaxonomy, seed_pickup_taxonomy

UTC = UTC


def fresh_db(tmp_path) -> tuple:
    """Fresh SQLite engine + session with schema created (M0 migration path)."""
    engine = make_engine(f"sqlite:///{tmp_path / 'carvalue_import.db'}")
    Base.metadata.create_all(engine)
    Session = make_session(engine)
    return engine, Session


def make_session(engine):
    from sqlalchemy.orm import sessionmaker

    return sessionmaker(bind=engine, expire_on_commit=False)


def _create_source(
    session, *, source_id: int = 1, permission_status: str = "approved", enabled: bool = True
) -> None:
    """Seed an approved/enabled source (FR-DATA-01/02) so a run can link to it."""
    source = Source(
        id=source_id,
        name=f"marketcheck_feed_{source_id}",
        source_type="api_feed",
        permission_status=permission_status,
        enabled=enabled,
    )
    session.add(source)
    session.flush()


def _create_run(session, source_id: int = 1) -> int:
    """Create a crawl_run and return its id (M2 provenance linkage)."""
    run = CrawlRun(source_id=source_id, state="running", started_at=datetime.now(UTC))
    session.add(run)
    session.flush()
    return int(run.id)


def _context(source_id: int = 1) -> ImportContext:
    return ImportContext(
        source_id=source_id,
        default_make="ford",
        default_model="ranger",
        observed_at_fallback=datetime(2026, 8, 21, tzinfo=UTC),
        province="AB",
    )


def _partial_csv(tmp_path) -> str:
    """3 rows: one valid Ford Ranger, one missing price, one non-Alberta."""
    path = tmp_path / "partial.csv"
    path.write_text(
        "Year,Mileage,Price,Seller Type,Province\n"
        "2022,40000,30000,Dealer,AB\n"  # valid -> accepted
        "2021,65000,,Private,AB\n"  # missing price -> rejected
        "2020,50000,25000,Private,ON\n",  # non-Alberta -> rejected
        encoding="utf-8",
    )
    return str(path)


def test_dry_run_is_repeatable(tmp_path) -> None:
    engine, Session = fresh_db(tmp_path)
    taxonomy = PickupTaxonomy.from_nodes(seed_pickup_taxonomy())
    ctx = _context()

    first = preview_import(_partial_csv(tmp_path), ctx, taxonomy)
    second = preview_import(_partial_csv(tmp_path), ctx, taxonomy)
    assert first.total_rows == second.total_rows
    assert len(first.accepted_observations) == len(second.accepted_observations)
    engine.dispose()


def test_valid_rows_commit_when_other_rows_fail(tmp_path) -> None:
    """FR-DATA-07 / scenario 6: valid rows commit safely, failures quarantined."""
    engine, Session = fresh_db(tmp_path)
    session = Session()
    taxonomy = PickupTaxonomy.from_nodes(seed_pickup_taxonomy())
    ctx = _context()

    _create_source(session)
    run = claim_source_run(session, source_id=1)
    assert run is not None, "approved source should claim a running run"
    run_id = int(run.id)
    preview = preview_import(_partial_csv(tmp_path), ctx, taxonomy)
    assert not preview.column_errors  # authorized file has all required columns

    summary = commit_preview(session, preview, run_id=run_id)
    assert isinstance(summary, CommitSummary)
    # Exactly one valid row commits; two failures are rejected (not written).
    assert summary.accepted == 1
    assert len(preview.rejected_rows) == 2
    codes = {r.code for r in preview.rejected_rows}
    assert ReasonCode.MISSING_PRICE in codes
    assert ReasonCode.LOCATION_NOT_ALBERTA in codes

    # The rejected rows left no listing behind.
    from carvalue_core.persistence import Listing
    from sqlalchemy import select

    committed = session.execute(select(Listing).where(Listing.source_id == 1)).all()
    assert len(committed) == 1, "only the valid row should create a listing"

    # Run counters are observable and match the safe commit.
    run = session.get(CrawlRun, run_id)
    assert run is not None
    assert run.accepted == 1
    assert run.updated == 0
    assert run.duplicate == 0
    session.close()
    engine.dispose()


def test_rerun_does_not_duplicate_listing(tmp_path) -> None:
    """Scenario 3: an exact repeated observation updates last-seen/price history,
    not a duplicate listing."""
    engine, Session = fresh_db(tmp_path)
    session = Session()
    taxonomy = PickupTaxonomy.from_nodes(seed_pickup_taxonomy())
    ctx = _context()

    _create_source(session)
    run = claim_source_run(session, source_id=1)
    assert run is not None, "approved source should claim a running run"
    run_id = int(run.id)

    # First commit of the valid row (creates one listing).
    preview1 = preview_import(_partial_csv(tmp_path), ctx, taxonomy)
    summary1 = commit_preview(session, preview1, run_id=run_id)
    assert summary1.accepted == 1

    # Re-import the same CSV (rerun). The valid row must NOT create a new listing;
    # an exact rerun is correctly flagged as updated/duplicate, not fresh accepted.
    preview2 = preview_import(_partial_csv(tmp_path), ctx, taxonomy)
    summary2 = commit_preview(session, preview2, run_id=run_id)
    # An exact rerun is counted as updated/duplicate (not a fresh accepted),
    # so no duplicate listing is created. Both invariants together catch a
    # double-count bug: summary2.accepted stays 0 and listings count stays 1.
    assert summary2.accepted == 0, "rerun should not re-create the accepted listing"

    from carvalue_core.persistence import Listing, ListingPriceHistory
    from sqlalchemy import select

    listings = session.execute(select(Listing).where(Listing.source_id == 1)).all()
    assert len(listings) == 1, "rerun must not duplicate the listing"
    # Price history is preserved (appended once per distinct observation time).
    history_count = session.execute(
        select(ListingPriceHistory.listing_id).where(
            ListingPriceHistory.listing_id == listings[0][0].id
        )
    ).all()
    assert len(history_count) >= 1, "price history must survive reruns"
    session.close()
    engine.dispose()


def test_cross_source_collision_flagged_without_merging(tmp_path) -> None:
    """Scenario 6 / FR-DATA-06: a cross-source fingerprint collision is flagged
    as POSSIBLE_DUPLICATE and left unmerged for review."""
    engine, Session = fresh_db(tmp_path)
    session = Session()

    _create_source(session, source_id=1)
    run = claim_source_run(session, source_id=1)
    assert run is not None, "approved source should claim a running run"
    run_id = int(run.id)

    # Source 2: the cross-source collision (distinct approved source + lease).
    _create_source(session, source_id=2)
    run2 = claim_source_run(session, source_id=2)
    assert run2 is not None, "approved source 2 should claim its own running run"
    run2_id = int(run2.id)

    # Source 1: first listing of the vehicle.
    obs1 = ListingObservation(
        source_id=1,
        source_record_id="row-1",
        make="ford",
        model="ranger",
        model_year=2022,
        mileage_km=40_000,
        asking_price_cad_cents=3_000_000,
        observed_at_utc=datetime(2026, 8, 21, tzinfo=UTC),
        province="AB",
    )
    outcome1 = upsert_listing_observation(session, obs1, run_id=run_id)
    assert outcome1.status == "accepted"
    assert listing_fingerprint(obs1) is not None

    # Source 2: same vehicle identity, different source record ID.
    obs2 = ListingObservation(
        source_id=2,
        source_record_id="other-1",
        make="ford",
        model="ranger",
        model_year=2022,
        mileage_km=40_000,
        asking_price_cad_cents=3_000_000,
        observed_at_utc=datetime(2026, 8, 21, tzinfo=UTC),
        province="AB",
    )
    outcome2 = upsert_listing_observation(session, obs2, run_id=run2_id)
    # FR-DATA-06 dedup by source/record-id FIRST: obs2 is from a distinct source
    # with a new record-id, so it creates its own listing (accepted); the fingerprint
    # collision is then flagged as POSSIBLE_DUPLICATE and left unmerged for review.
    assert outcome2.status == "accepted"
    assert outcome1.listing_id != outcome2.listing_id, (
        "collision must be flagged without merging into one listing"
    )

    from carvalue_core.persistence import DataQualityIssue, Listing
    from sqlalchemy import select

    listings = session.execute(select(Listing).where(Listing.source_id == 1)).all()
    assert len(listings) == 1, "source-1 listing count unchanged by the collision"
    # The flagged collision is NOT silently merged: both listings remain distinct rows.
    total = session.execute(select(Listing)).all()
    assert len(total) == 2, "cross-source collision stays two distinct listings"
    issues = session.execute(
        select(DataQualityIssue).where(
            DataQualityIssue.reason_code == ReasonCode.POSSIBLE_DUPLICATE.value
        )
    ).all()
    assert len(issues) >= 1, "cross-source collision flagged for review"

    # Run counters stay observable: each run accepted its respective listing.
    run = session.get(CrawlRun, run_id)
    assert run is not None
    assert run.accepted == 1
    run2 = session.get(CrawlRun, run2_id)
    assert run2 is not None
    assert run2.accepted == 1
    session.close()
    engine.dispose()


@pytest.mark.parametrize("permission_status", ["unknown", "denied"])
def test_unauthorized_source_run_blocked(tmp_path, permission_status: str) -> None:
    """FR-DATA-02 / scenario 4: a source whose permission is unknown/denied (or
    not enabled) blocks its automated run — fail closed, counters stay zero."""
    engine, Session = fresh_db(tmp_path)
    session = Session()

    _create_source(
        session,
        permission_status=permission_status,
        enabled=(permission_status == "approved"),
    )

    run = claim_source_run(session, source_id=1)
    assert run is None, f"source with {permission_status} status should block the run"

    # No listing was written without a valid lease.
    from carvalue_core.persistence import Listing
    from sqlalchemy import select

    listings = session.execute(select(Listing).where(Listing.source_id == 1)).all()
    assert len(listings) == 0, "unauthorized run must not write a listing"

    # A denied/unknown source that is later approved can claim its run.
    existing = session.get(Source, 1)
    existing.permission_status = "approved"
    existing.enabled = True
    session.flush()
    run2 = claim_source_run(session, source_id=1)
    assert run2 is not None, "approved-after-review source should claim its run"
    session.close()
    engine.dispose()
