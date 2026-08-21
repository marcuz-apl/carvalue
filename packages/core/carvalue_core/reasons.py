"""Stable rejection/quarantine reason codes and safe user messages.

Error handling convention (AGENTS.md): return a stable code plus a safe,
non-technical message; detailed diagnostics stay in protected logs. Codes are
grouped by where they occur: row-level import problems, source-policy gates,
and valuation evidence rules.
"""

from __future__ import annotations

from enum import Enum


class ReasonCode(str, Enum):
    # --- Row-level import / normalization rejections -----------------------
    MISSING_YEAR = "missing_year"
    MISSING_MILEAGE = "missing_mileage"
    MISSING_PRICE = "missing_price"
    NON_INTEGER_FIELD = "non_integer_field"
    YEAR_OUT_OF_RANGE = "year_out_of_range"
    MILEAGE_OUT_OF_RANGE = "mileage_out_of_range"
    PRICE_NON_POSITIVE = "price_non_positive"
    PRICE_ABOVE_PLAUSIBLE_MAX = "price_above_plausible_max"
    LOCATION_NOT_ALBERTA = "location_not_alberta"
    UNRECOGNIZED_MAKE_MODEL = "unrecognized_make_model"
    UNRECOGNIZED_VALUE = "unrecognized_value"  # known field, value outside allowlist
    COLUMN_NOT_FOUND = "column_not_found"

    # --- Source policy gate (fail closed) ----------------------------------
    SOURCE_PERMISSION_BLOCKED = "source_permission_blocked"
    SOURCE_POLICY_REVIEW_EXPIRED = "source_policy_review_expired"
    SOURCE_DISABLED = "source_disabled"
    SOURCE_RUN_LEASE_HELD = "source_run_lease_held"

    # --- Ingestion run outcomes (counters, not errors) ----------------------
    DUPLICATE_OBSERVATION = "duplicate_observation"
    POSSIBLE_DUPLICATE = "possible_duplicate"  # cross-source fingerprint collision; flagged for review

    # --- Valuation evidence / refusal rules ---------------------------------
    NO_ACTIVE_MODEL = "no_active_model"
    SPARSE_SEGMENT = "sparse_segment"
    OUT_OF_TRAINING_DOMAIN = "out_of_training_domain"
    STALE_MODEL = "stale_model"
    TOO_WIDE_INTERVAL = "too_wide_interval"


_SAFE_MESSAGES: dict[ReasonCode, str] = {
    ReasonCode.MISSING_YEAR: "Model year is missing.",
    ReasonCode.MISSING_MILEAGE: "Odometer reading (km) is missing.",
    ReasonCode.MISSING_PRICE: "Asking price (CAD) is missing.",
    ReasonCode.NON_INTEGER_FIELD: "A numeric field could not be read as a whole number.",
    ReasonCode.YEAR_OUT_OF_RANGE: "Model year is outside the supported range.",
    ReasonCode.MILEAGE_OUT_OF_RANGE: "Odometer reading is outside the plausible range.",
    ReasonCode.PRICE_NON_POSITIVE: "Asking price must be greater than zero.",
    ReasonCode.PRICE_ABOVE_PLAUSIBLE_MAX: "Asking price is above the plausible maximum.",
    ReasonCode.LOCATION_NOT_ALBERTA: "Listing location is not in Alberta.",
    ReasonCode.UNRECOGNIZED_MAKE_MODEL: "Make/model combination is not a supported pickup.",
    ReasonCode.UNRECOGNIZED_VALUE: "A field value could not be mapped to a known option; it was left blank.",
    ReasonCode.COLUMN_NOT_FOUND: "A required column could not be found in the file.",
    ReasonCode.SOURCE_PERMISSION_BLOCKED: (
        "Source permission has not been confirmed; collection stayed off."
    ),
    ReasonCode.SOURCE_POLICY_REVIEW_EXPIRED: (
        "The source policy review has expired; collection stayed off until re-reviewed."
    ),
    ReasonCode.SOURCE_DISABLED: "This source is currently disabled.",
    ReasonCode.SOURCE_RUN_LEASE_HELD: "Another run for this source is already in progress.",
    ReasonCode.DUPLICATE_OBSERVATION: "Same observation was already recorded; no change made.",
    ReasonCode.POSSIBLE_DUPLICATE: (
        "This listing looks identical to one already collected from another source."
    ),
    ReasonCode.NO_ACTIVE_MODEL: "No valuation model has been promoted yet.",
    ReasonCode.SPARSE_SEGMENT: (
        "Not enough comparable listings for this vehicle to support an estimate."
    ),
    ReasonCode.OUT_OF_TRAINING_DOMAIN: (
        "This vehicle is outside the range the current model was trained on."
    ),
    ReasonCode.STALE_MODEL: "The current model or its data is older than the freshness limit.",
    ReasonCode.TOO_WIDE_INTERVAL: (
        "Comparable evidence is too weak to produce a narrow, useful price range."
    ),
}


def safe_message(code: ReasonCode) -> str:
    """Safe, user-facing message for a reason code (never leaks internals)."""
    return _SAFE_MESSAGES[code]
