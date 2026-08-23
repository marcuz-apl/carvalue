"""Permission metadata and fail-closed preflight for automated sources."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from math import isfinite

from carvalue_core.reasons import ReasonCode

VALUATION_SAFE_PERMITTED_FIELDS = frozenset(
    {
        "asking_price_cad_cents",
        "box_length_m",
        "cab_style",
        "city",
        "content_checksum_sha256",
        "drivetrain",
        "fetched_at",
        "first_seen_at",
        "last_seen_at",
        "make",
        "mileage_km",
        "model",
        "model_year",
        "observed_at",
        "price_cad",
        "province",
        "region",
        "seller_type",
        "source_record_id",
        "trim",
        "year",
    }
)


class SourceType(str, Enum):  # noqa: UP042 - public contract requires str/Enum compatibility
    MANUAL_IMPORT = "manual_import"
    API_FEED = "api_feed"
    CRAWLER = "crawler"
    OPEN_DATA = "open_data"


class PermissionStatus(str, Enum):  # noqa: UP042 - public contract requires str/Enum compatibility
    UNKNOWN = "unknown"
    APPROVED = "approved"
    DENIED = "denied"


@dataclass(frozen=True)
class SourcePolicy:
    source_id: int
    name: str
    source_type: SourceType
    origin: str
    permission_status: PermissionStatus
    permission_basis: str | None
    policy_reviewed_at_utc: datetime | None
    policy_review_expires_at_utc: datetime | None
    terms_reviewed_at_utc: datetime | None
    terms_review_evidence: str | None
    robots_reviewed_at_utc: datetime | None
    robots_review_evidence: str | None
    permitted_fields: frozenset[str]
    retention_deadline_utc: datetime | None
    attribution: str | None
    rate_limit_per_second: float | None
    enabled: bool
    adapter_version: str | None
    parser_version: str | None
    owner_notes: str | None = None


@dataclass(frozen=True)
class PreflightDecision:
    allowed: bool
    reason_code: ReasonCode | None = None


def _is_utc(value: datetime | None) -> bool:
    return (
        value is not None and value.tzinfo is not None and value.utcoffset() == UTC.utcoffset(value)
    )


def _has_current_review_evidence(
    reviewed_at_utc: datetime | None, evidence: str | None, now_utc: datetime
) -> bool:
    if not _is_utc(reviewed_at_utc) or not evidence or not evidence.strip():
        return False
    assert reviewed_at_utc is not None
    return reviewed_at_utc <= now_utc


def _has_required_policy_metadata(policy: SourcePolicy, now_utc: datetime) -> bool:
    if (
        isinstance(policy.source_id, bool)
        or not isinstance(policy.source_id, int)
        or policy.source_id <= 0
        or not policy.name.strip()
        or not policy.origin.strip()
    ):
        return False
    if not policy.permission_basis or not policy.permission_basis.strip():
        return False
    reviewed_at_utc = policy.policy_reviewed_at_utc
    if not _is_utc(reviewed_at_utc):
        return False
    assert reviewed_at_utc is not None
    if reviewed_at_utc > now_utc:
        return False
    compliance_reviews = (
        (policy.terms_reviewed_at_utc, policy.terms_review_evidence),
        (policy.robots_reviewed_at_utc, policy.robots_review_evidence),
    )
    if any(
        not _has_current_review_evidence(reviewed_at_utc, evidence, now_utc)
        for reviewed_at_utc, evidence in compliance_reviews
    ):
        return False
    if not policy.permitted_fields or not policy.permitted_fields.issubset(
        VALUATION_SAFE_PERMITTED_FIELDS
    ):
        return False
    retention_deadline_utc = policy.retention_deadline_utc
    if not _is_utc(retention_deadline_utc):
        return False
    assert retention_deadline_utc is not None
    if retention_deadline_utc <= now_utc:
        return False
    if not policy.attribution or not policy.attribution.strip():
        return False
    if not policy.adapter_version or not policy.adapter_version.strip():
        return False
    if not policy.parser_version or not policy.parser_version.strip():
        return False
    return (
        policy.rate_limit_per_second is not None
        and isfinite(policy.rate_limit_per_second)
        and policy.rate_limit_per_second > 0
    )


def preflight_automated_source(policy: SourcePolicy, now_utc: datetime) -> PreflightDecision:
    """Return a fail-closed decision for automated source execution."""
    if not policy.enabled:
        return PreflightDecision(False, ReasonCode.SOURCE_DISABLED)

    if policy.permission_status is not PermissionStatus.APPROVED:
        return PreflightDecision(False, ReasonCode.SOURCE_PERMISSION_BLOCKED)

    if not _is_utc(now_utc) or policy.policy_review_expires_at_utc is None:
        return PreflightDecision(False, ReasonCode.SOURCE_POLICY_REVIEW_EXPIRED)
    if (
        not _is_utc(policy.policy_review_expires_at_utc)
        or policy.policy_review_expires_at_utc <= now_utc
    ):
        return PreflightDecision(False, ReasonCode.SOURCE_POLICY_REVIEW_EXPIRED)

    if not _has_required_policy_metadata(policy, now_utc):
        return PreflightDecision(False, ReasonCode.SOURCE_PERMISSION_BLOCKED)

    return PreflightDecision(True)
