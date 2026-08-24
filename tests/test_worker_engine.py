"""Unit and integration tests for worker lease engine, fail-closed preflight, and batch runner."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from carvalue_core.listings import ListingObservation
from carvalue_core.persistence import (
    Base,
    Listing,
    Source,
    SourceRun,
    make_engine,
    new_session_factory,
)
from carvalue_core.reasons import ReasonCode
from carvalue_worker.engine import (
    SourceLeaseManager,
    SourcePreflightChecker,
    WorkerJobRunner,
)


def create_test_source(
    session,
    source_id: int = 1,
    permission_status: str = "approved",
    enabled: bool = True,
    reviewed_days_ago: int = 10,
) -> Source:
    reviewed_at = (
        datetime.now(UTC) - timedelta(days=reviewed_days_ago)
        if reviewed_days_ago is not None
        else None
    )
    source = Source(
        id=source_id,
        name=f"test_source_{source_id}",
        source_type="api_feed",
        permission_status=permission_status,
        enabled=enabled,
        policy_reviewed_at=reviewed_at,
    )
    session.add(source)
    session.flush()
    return source


def test_preflight_denies_unapproved_or_disabled_sources(tmp_path) -> None:
    db_path = tmp_path / "test_worker_preflight.db"
    engine = make_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    SessionLocal = new_session_factory(engine)

    with SessionLocal() as session:
        # 1. Disabled source
        s_disabled = create_test_source(session, source_id=1, enabled=False)
        res1 = SourcePreflightChecker.evaluate(s_disabled)
        assert res1.passed is False
        assert res1.reason_code == ReasonCode.SOURCE_DISABLED

        # 2. Denied / unapproved source
        s_unapproved = create_test_source(session, source_id=2, permission_status="unknown")
        res2 = SourcePreflightChecker.evaluate(s_unapproved)
        assert res2.passed is False
        assert res2.reason_code == ReasonCode.SOURCE_PERMISSION_BLOCKED

        # 3. Expired policy review (> 90 days)
        s_expired = create_test_source(session, source_id=3, reviewed_days_ago=95)
        res3 = SourcePreflightChecker.evaluate(s_expired)
        assert res3.passed is False
        assert res3.reason_code == ReasonCode.SOURCE_POLICY_REVIEW_EXPIRED

        # 4. Valid approved source
        s_valid = create_test_source(session, source_id=4, reviewed_days_ago=15)
        res4 = SourcePreflightChecker.evaluate(s_valid)
        assert res4.passed is True

    engine.dispose()


def test_lease_manager_claims_and_blocks_concurrent_runs(tmp_path) -> None:
    db_path = tmp_path / "test_worker_leases.db"
    engine = make_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    SessionLocal = new_session_factory(engine)

    with SessionLocal() as session:
        create_test_source(session, source_id=1)

        # 1. Claim initial lease
        run1 = SourceLeaseManager.claim_lease(session, source_id=1, lease_seconds=300)
        session.commit()
        assert run1 is not None
        assert run1.status == "running"
        assert run1.lease_expires_at is not None

        # 2. Second worker attempts concurrent run on same source -> blocked
        run2 = SourceLeaseManager.claim_lease(session, source_id=1, lease_seconds=300)
        assert run2 is None

        # 3. Renew lease
        renewed = SourceLeaseManager.renew_lease(session, run_id=run1.id, lease_seconds=600)
        assert renewed is True

        # 4. Release lease
        SourceLeaseManager.release_lease(session, run_id=run1.id, final_status="completed")
        session.commit()

        # 5. Third worker can now claim lease after release
        run3 = SourceLeaseManager.claim_lease(session, source_id=1, lease_seconds=300)
        assert run3 is not None
        assert run3.status == "running"

    engine.dispose()


def test_worker_job_runner_executes_batch_with_counters(tmp_path) -> None:
    db_path = tmp_path / "test_worker_job.db"
    engine = make_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    SessionLocal = new_session_factory(engine)

    with SessionLocal() as session:
        create_test_source(session, source_id=1, permission_status="approved", enabled=True)

        observations = [
            ListingObservation(
                source_id=1,
                source_record_id=f"worker-test-{i}",
                make="ford",
                model="ranger",
                trim="xlt",
                drivetrain="4wd",
                seller_type="dealer",
                model_year=2022,
                mileage_km=30000 + i * 1000,
                asking_price_cad_cents=3200000 + i * 10000,
                observed_at_utc=datetime(2026, 8, 20, tzinfo=UTC),
                province="AB",
            )
            for i in range(5)
        ]

        runner = WorkerJobRunner(session)
        run, preflight = runner.run_ingestion_batch(source_id=1, observations=observations)
        session.commit()

        assert preflight.passed is True
        assert run is not None
        assert run.status == "completed"
        assert run.records_fetched == 5
        assert run.records_accepted == 5
        assert run.records_rejected == 0

        # Confirm listings were written
        listings = session.execute(select(Listing).where(Listing.source_id == 1)).scalars().all()
        assert len(listings) == 5

    engine.dispose()
