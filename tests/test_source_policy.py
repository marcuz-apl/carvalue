"""M1 contract test: automated source preflight fails closed without current approval.

Roadmap M1 exit gate: "a source canNOT pass automated preflight without current
approval." PRD FR-DATA-02 and acceptance scenario 4. ``unknown``, ``denied``,
disabled, expired, and incomplete permission records each return a stable blocked
decision (fail closed) before any network adapter runs.
"""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from carvalue_core.reasons import ReasonCode
from carvalue_core.source_policy import (
    VALUATION_SAFE_PERMITTED_FIELDS,
    PermissionStatus,
    PreflightDecision,
    SourcePolicy,
    SourceType,
    preflight_automated_source,
)

UTC = UTC


def _now() -> datetime:
    return datetime(2026, 8, 23, 12, 0, 0, tzinfo=UTC)


def make_valid_policy(**overrides) -> SourcePolicy:
    """A fully-compliant approved source; override any field to break it."""
    base = dict(
        source_id=1,
        name="MarketCheck licensed feed",
        source_type=SourceType.API_FEED,
        origin="https://marketcheck.com/supply",
        permission_status=PermissionStatus.APPROVED,
        permission_basis="Licensed dataset; written ML/storage rights granted",
        policy_reviewed_at_utc=datetime(2026, 8, 1, tzinfo=UTC),
        policy_review_expires_at_utc=datetime(2027, 8, 1, tzinfo=UTC),
        terms_reviewed_at_utc=datetime(2026, 8, 1, tzinfo=UTC),
        terms_review_evidence="许可-ML-storage",
        robots_reviewed_at_utc=datetime(2026, 8, 1, tzinfo=UTC),
        robots_review_evidence="robots approved",
        permitted_fields=frozenset({"asking_price_cad_cents", "mileage_km"}),
        retention_deadline_utc=datetime(2027, 1, 1, tzinfo=UTC),
        attribution="MarketCheck via CarValue",
        rate_limit_per_second=2.0,
        enabled=True,
        adapter_version="v1.2",
        parser_version="v1",
    )
    base.update(overrides)
    return SourcePolicy(**base)


def test_unknown_permission_fails_closed() -> None:
    decision = preflight_automated_source(
        make_valid_policy(permission_status=PermissionStatus.UNKNOWN), _now()
    )
    assert isinstance(decision, PreflightDecision)
    assert decision.allowed is False
    assert decision.reason_code == ReasonCode.SOURCE_PERMISSION_BLOCKED


def test_denied_permission_fails_closed() -> None:
    decision = preflight_automated_source(
        make_valid_policy(permission_status=PermissionStatus.DENIED), _now()
    )
    assert decision.allowed is False
    assert decision.reason_code == ReasonCode.SOURCE_PERMISSION_BLOCKED


def test_disabled_source_fails_closed() -> None:
    # Even an approved, current source must fail closed when disabled.
    decision = preflight_automated_source(make_valid_policy(enabled=False), _now())
    assert decision.allowed is False
    assert decision.reason_code == ReasonCode.SOURCE_DISABLED


def test_expired_policy_review_fails_closed() -> None:
    expired = _now() - timedelta(days=1)
    decision = preflight_automated_source(
        make_valid_policy(policy_review_expires_at_utc=expired), _now()
    )
    assert decision.allowed is False
    assert decision.reason_code == ReasonCode.SOURCE_POLICY_REVIEW_EXPIRED


def test_missing_expiry_record_fails_closed() -> None:
    decision = preflight_automated_source(
        make_valid_policy(policy_review_expires_at_utc=None), _now()
    )
    assert decision.allowed is False
    assert decision.reason_code == ReasonCode.SOURCE_POLICY_REVIEW_EXPIRED


@pytest.mark.parametrize(
    "now",
    [
        datetime(2026, 8, 23, 12, 0, 0),  # naive, no zone
        datetime(
            2026, 8, 23, 12, 0, 0, tzinfo=timezone(timedelta(hours=-8))
        ),  # fixed-offset non-UTC zone
    ],
)
def test_non_utc_now_fails_closed(now: datetime) -> None:
    decision = preflight_automated_source(make_valid_policy(), now)
    assert decision.allowed is False, f"now={now!r} should fail closed"
    assert decision.reason_code == ReasonCode.SOURCE_POLICY_REVIEW_EXPIRED


def test_incomplete_terms_evidence_fails_closed() -> None:
    decision = preflight_automated_source(make_valid_policy(terms_review_evidence="  "), _now())
    assert decision.allowed is False
    assert decision.reason_code == ReasonCode.SOURCE_PERMISSION_BLOCKED


def test_incomplete_robots_evidence_fails_closed() -> None:
    decision = preflight_automated_source(make_valid_policy(robots_review_evidence=""), _now())
    assert decision.allowed is False
    assert decision.reason_code == ReasonCode.SOURCE_PERMISSION_BLOCKED


def test_expired_retention_deadline_fails_closed() -> None:
    decision = preflight_automated_source(
        make_valid_policy(retention_deadline_utc=_now() - timedelta(days=1)), _now()
    )
    assert decision.allowed is False
    assert decision.reason_code == ReasonCode.SOURCE_PERMISSION_BLOCKED


def test_permitted_fields_not_subset_fails_closed() -> None:
    leaky = frozenset({"asking_price_cad_cents", "mileage_km", "seller_phone"})
    decision = preflight_automated_source(make_valid_policy(permitted_fields=leaky), _now())
    assert decision.allowed is False
    assert decision.reason_code == ReasonCode.SOURCE_PERMISSION_BLOCKED


def test_rate_limit_non_positive_fails_closed() -> None:
    for bad in (0.0, -1.0):
        decision = preflight_automated_source(make_valid_policy(rate_limit_per_second=bad), _now())
        assert decision.allowed is False
        assert decision.reason_code == ReasonCode.SOURCE_PERMISSION_BLOCKED


def test_valid_current_approved_source_passes() -> None:
    decision = preflight_automated_source(make_valid_policy(), _now())
    assert decision.allowed is True
    assert decision.reason_code is None


def test_permitted_fields_are_valuation_safe() -> None:
    """The permissioned set excludes seller identity, contact, free text, and photos."""
    personal = {
        "seller_name",
        "seller_phone",
        "seller_email",
        "free_text",
        "photo_url",
        "vin",
        "canonical_url_raw",
    }
    assert not (personal & VALUATION_SAFE_PERMITTED_FIELDS)
