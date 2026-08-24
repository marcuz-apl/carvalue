"""Background worker lease engine, fail-closed preflight, and job orchestration.

Implements PRD Section 10 (Deny-by-default data acquisition) and FR-DATA-01/02/03:
- SQLite-safe run leases (bounded duration, single-runner guarantee).
- Fail-closed source preflight (permission status, review expiry, enabled flag).
- Idempotent ingestion execution with comprehensive run counters.
- America/Edmonton timezone support for scheduled tasks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from carvalue_core.listings import ListingObservation
from carvalue_core.persistence import (
    Source,
    SourcePolicy,
    SourceRun,
    upsert_listing_observation,
)
from carvalue_core.reasons import ReasonCode, safe_message
from carvalue_core.security import record_audit_event

logger = logging.getLogger(__name__)

EDMONTON_TZ = ZoneInfo("America/Edmonton")
DEFAULT_LEASE_SECONDS = 300
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
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
        now: datetime | None = None,
    ) -> SourceRun | None:
        """Attempt to claim an exclusive run lease for the source.

        Returns a new running SourceRun if claimed, None if another active lease is held.
        """
        now_utc = now or datetime.now(UTC)

        # Check for active running leases
        active_run = session.execute(
            select(SourceRun).where(
                SourceRun.source_id == source_id,
                SourceRun.status == "running",
            )
        ).scalar_one_or_none()

        if active_run:
            if active_run.lease_expires_at and active_run.lease_expires_at > now_utc:
                # Active lease held by another worker
                return None
            # Stale lease expired: mark as failed/expired
            active_run.status = "failed"
            active_run.finished_at = now_utc
            active_run.error_message = "Worker lease expired before completion"
            session.flush()

        # Create new running run
        expires_at = now_utc + timedelta(seconds=lease_seconds)
        new_run = SourceRun(
            source_id=source_id,
            status="running",
            started_at=now_utc,
            lease_expires_at=expires_at,
            records_fetched=0,
            records_accepted=0,
            records_updated=0,
            records_duplicate=0,
            records_quarantined=0,
            records_rejected=0,
        )
        session.add(new_run)
        session.flush()
        return new_run

    @staticmethod
    def renew_lease(
        session: Session,
        run_id: int,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
        now: datetime | None = None,
    ) -> bool:
        """Extend an existing lease for long-running batches."""
        now_utc = now or datetime.now(UTC)
        run = session.get(SourceRun, run_id)
        if run and run.status == "running":
            run.lease_expires_at = now_utc + timedelta(seconds=lease_seconds)
            session.flush()
            return True
        return False

    @staticmethod
    def release_lease(
        session: Session,
        run_id: int,
        final_status: str = "completed",
        error_message: str | None = None,
        now: datetime | None = None,
    ) -> None:
        """Release the lease and record the final run completion state."""
        now_utc = now or datetime.now(UTC)
        run = session.get(SourceRun, run_id)
        if run:
            run.status = final_status
            run.finished_at = now_utc
            run.error_message = error_message
            run.lease_expires_at = None
            session.flush()


class WorkerJobRunner:
    """Execute ingestion batches with preflight gates, leases, and run counters."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def run_ingestion_batch(
        self,
        source_id: int,
        observations: list[ListingObservation],
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> tuple[SourceRun | None, PreflightResult]:
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
                actor_type="worker",
                actor_ref=f"source:{source_id}",
                action="ingestion.preflight_rejected",
                target_type="source",
                target_ref=str(source_id),
                outcome="rejected",
                details_json={"reason": preflight.reason_code, "message": preflight.message},
            )
            return None, preflight

        # 2. Claim exclusive lease
        run = SourceLeaseManager.claim_lease(
            self.session, source_id=source_id, lease_seconds=lease_seconds
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
                run.records_fetched += 1
                try:
                    outcome = upsert_listing_observation(
                        session=self.session,
                        obs=obs,
                        run_id=run_id,
                    )
                except Exception as row_exc:
                    run.records_rejected += 1
                    logger.warning("Observation processing failed: %s", row_exc)

            SourceLeaseManager.release_lease(
                self.session, run_id=run_id, final_status="completed"
            )
            record_audit_event(
                session=self.session,
                actor_type="worker",
                actor_ref=f"source:{source_id}",
                action="ingestion.completed",
                target_type="source_run",
                target_ref=str(run_id),
                outcome="ok",
                details_json={
                    "fetched": run.records_fetched,
                    "accepted": run.records_accepted,
                    "updated": run.records_updated,
                    "duplicate": run.records_duplicate,
                    "quarantined": run.records_quarantined,
                    "rejected": run.records_rejected,
                },
            )
            return run, preflight
        except Exception as exc:
            SourceLeaseManager.release_lease(
                self.session, run_id=run_id, final_status="failed", error_message=str(exc)
            )
            record_audit_event(
                session=self.session,
                actor_type="worker",
                actor_ref=f"source:{source_id}",
                action="ingestion.failed",
                target_type="source_run",
                target_ref=str(run_id),
                outcome="failed",
                details_json={"error": str(exc)},
            )
            raise
