"""Background worker lease engine, fail-closed preflight, and job orchestration.

Implements PRD Section 10 (Deny-by-default data acquisition) and FR-DATA-01/02/03:
- SQLite-safe run leases (bounded duration, single-runner guarantee via CrawlRun).
- Fail-closed source preflight (permission status, review expiry, enabled flag).
- Idempotent ingestion execution with comprehensive run counters.
- America/Edmonton timezone support for scheduled tasks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from carvalue_core.listings import ListingObservation
from carvalue_core.persistence import (
    CrawlRun,
    Source,
    claim_source_run,
    upsert_listing_observation,
)
from carvalue_core.reasons import ReasonCode, safe_message
from carvalue_core.security import record_audit_event

logger = logging.getLogger(__name__)

EDMONTON_TZ = ZoneInfo("America/Edmonton")
MAX_POLICY_AGE_DAYS = 90


@dataclass(frozen=True)
class PreflightResult:
    passed: bool
    reason_code: ReasonCode | None = None
    message: str = "Preflight passed"


class SourcePreflightChecker:
    """Evaluate whether a source is legally and operationally permitted to run."""

    @staticmethod
    def evaluate(source: Source, now: datetime | None = None) -> PreflightResult:
        now_utc = now or datetime.now(UTC)

        if not source.enabled:
            return PreflightResult(
                passed=False,
                reason_code=ReasonCode.SOURCE_DISABLED,
                message=safe_message(ReasonCode.SOURCE_DISABLED),
            )

        if source.permission_status != "approved":
            return PreflightResult(
                passed=False,
                reason_code=ReasonCode.SOURCE_PERMISSION_BLOCKED,
                message=safe_message(ReasonCode.SOURCE_PERMISSION_BLOCKED),
            )

        # Policy review expiration check (90 days max)
        if source.policy_reviewed_at is None:
            return PreflightResult(
                passed=False,
                reason_code=ReasonCode.SOURCE_POLICY_REVIEW_EXPIRED,
                message=safe_message(ReasonCode.SOURCE_POLICY_REVIEW_EXPIRED),
            )

        review_age = (now_utc - source.policy_reviewed_at).days
        if review_age > MAX_POLICY_AGE_DAYS:
            return PreflightResult(
                passed=False,
                reason_code=ReasonCode.SOURCE_POLICY_REVIEW_EXPIRED,
                message=safe_message(ReasonCode.SOURCE_POLICY_REVIEW_EXPIRED),
            )

        return PreflightResult(passed=True)


class SourceLeaseManager:
    """Manage SQLite-safe distributed execution leases for ingestion sources."""

    @staticmethod
    def claim_lease(
        session: Session,
        source_id: int,
        correlation_id: str | None = None,
    ) -> CrawlRun | None:
        """Attempt to claim an exclusive run lease for the source.

        Returns a running CrawlRun if claimed, None if another active lease is held.
        """
        return claim_source_run(session, source_id, correlation_id=correlation_id)

    @staticmethod
    def release_lease(
        session: Session,
        run_id: int,
        final_state: str = "succeeded",
        error_message: str | None = None,
        now: datetime | None = None,
    ) -> None:
        """Release the lease and record the final run completion state."""
        now_utc = now or datetime.now(UTC)
        run = session.get(CrawlRun, run_id)
        if run:
            run.state = final_state
            run.finished_at = now_utc
            run.error_summary = error_message
            session.flush()


class WorkerJobRunner:
    """Execute ingestion batches with preflight gates, leases, and run counters."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def run_ingestion_batch(
        self,
        source_id: int,
        observations: list[ListingObservation],
        correlation_id: str | None = None,
    ) -> tuple[CrawlRun | None, PreflightResult]:
        """Execute a batch of listing observations for an approved source."""
        source = self.session.get(Source, source_id)
        if not source:
            return None, PreflightResult(
                passed=False,
                reason_code=ReasonCode.SOURCE_PERMISSION_BLOCKED,
                message="Source does not exist",
            )

        # 1. Fail-closed preflight check
        preflight = SourcePreflightChecker.evaluate(source)
        if not preflight.passed:
            record_audit_event(
                session=self.session,
                actor_type="system",
                actor_ref=f"source:{source_id}",
                action="ingestion.preflight_rejected",
                target_type="source",
                target_ref=str(source_id),
                outcome="blocked",
                details_json={"reason": preflight.reason_code, "message": preflight.message},
            )
            return None, preflight

        # 2. Claim exclusive database-backed lease
        run = SourceLeaseManager.claim_lease(
            self.session, source_id=source_id, correlation_id=correlation_id
        )
        if not run:
            return None, PreflightResult(
                passed=False,
                reason_code=ReasonCode.SOURCE_RUN_LEASE_HELD,
                message=safe_message(ReasonCode.SOURCE_RUN_LEASE_HELD),
            )

        run_id = int(run.id)

        # 3. Process observations
        try:
            for obs in observations:
                run.fetched += 1
                try:
                    upsert_listing_observation(
                        session=self.session,
                        obs=obs,
                        run_id=run_id,
                    )
                except Exception as row_exc:
                    run.failed += 1
                    logger.warning("Observation processing failed: %s", row_exc)

            SourceLeaseManager.release_lease(
                self.session, run_id=run_id, final_state="succeeded"
            )
            record_audit_event(
                session=self.session,
                actor_type="system",
                actor_ref=f"source:{source_id}",
                action="ingestion.completed",
                target_type="crawl_run",
                target_ref=str(run_id),
                outcome="ok",
                details_json={
                    "fetched": run.fetched,
                    "accepted": run.accepted,
                    "updated": run.updated,
                    "duplicate": run.duplicate,
                    "quarantined": run.quarantined,
                    "rejected": run.rejected,
                    "failed": run.failed,
                },
            )
            return run, preflight
        except Exception as exc:
            SourceLeaseManager.release_lease(
                self.session, run_id=run_id, final_state="failed", error_message=str(exc)
            )
            record_audit_event(
                session=self.session,
                actor_type="system",
                actor_ref=f"source:{source_id}",
                action="ingestion.failed",
                target_type="crawl_run",
                target_ref=str(run_id),
                outcome="error",
                details_json={"error": str(exc)},
            )
            raise
