# Milestone 1 Data Rights and Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish permission-safe source preflight, deterministic Alberta pickup taxonomy resolution, explicit CAD/km/UTC listing observations, and authorized local contract fixtures without making network calls or enabling collection.

**Architecture:** Keep M1 in `packages/core/carvalue_core` as pure, testable domain contracts. Source policy, taxonomy, units, listing observations, and spreadsheet normalization communicate through typed dataclasses and stable enums; SQLite persistence and automated adapters consume these contracts in later milestones. Fixtures remain local, sanitized, and rights-documented.

**Tech Stack:** Python 3.12, dataclasses, `datetime`, `Decimal`, pytest, Ruff, existing pandas/openpyxl spreadsheet reader.

**Spec:** `docs/superpowers/specs/2026-08-21-milestone-1-data-contracts-design.md`

## Global Constraints

- Keep MVP scope limited to Alberta used pickup trucks.
- Always use CAD and kilometres at system boundaries and in the UI; make conversions explicit and tested.
- Say “asking-price estimate,” not appraisal, guaranteed sale price, trade-in offer, or confirmed market value.
- Every valuation must include an uncertainty range, evidence/confidence label, valuation date, data freshness, comparable count, and disclaimer.
- Prefer “Insufficient Data” to fabricated precision for unsupported, sparse, stale, or out-of-distribution inputs.
- Never run, implement, schedule, or enable an automated source unless its source record documents permission/licence, terms and robots review, review date, allowed fields, retention, attribution, and rate limits.
- Never bypass login, CAPTCHA, paywall, bot control, robots directive, rate limit, or access restriction.
- Do not collect seller names, phone numbers, email addresses, personal free text, or photos.
- Money is integer CAD cents in storage and typed decimal/integer values in application logic; never binary float for persisted currency.
- Odometer is a non-negative integer in kilometres; timestamps are UTC.
- Validate untrusted spreadsheet cells as data; never evaluate formulas or execute content.
- Use stable error codes plus safe user messages; retain detailed diagnostics only in protected logs.
- No M1 code may make network calls, read credentials, enable a scheduler, or persist unlicensed source content.

---

## File Map

- Create `packages/core/carvalue_core/source_policy.py` for source types, permission metadata, and automated preflight decisions.
- Modify `packages/core/carvalue_core/reasons.py` only if a source-policy reason code is missing; keep codes stable and messages safe.
- Modify `packages/core/carvalue_core/taxonomy.py` to normalize aliases consistently at every hierarchy level and expose only canonical values.
- Modify `packages/core/carvalue_core/units.py` for a shared UTC boundary validator if the existing private persistence helper cannot be reused safely.
- Modify `packages/core/carvalue_core/listings.py` to make the observation timestamp typed/UTC and validate required canonical fields at construction.
- Modify `packages/core/carvalue_core/imports/spreadsheet.py` only where fixture parsing needs to consume the hardened contracts; do not add database writes or source fetching.
- Create `tests/test_source_policy.py` for permission/preflight behavior.
- Create `tests/test_taxonomy_contract.py` for normalization, hierarchy, and unsupported-value behavior.
- Create `tests/test_listing_contract.py` for CAD/km/UTC and privacy-boundary behavior.
- Create `tests/test_contract_fixtures.py` for the authorized fixture and required-field disappearance.
- Create `tests/fixtures/ford-ranger/valid.csv` containing a small sanitized vehicle-facts fixture.
- Create `tests/fixtures/ford-ranger/README.md` documenting origin, allowed development use, fields, and absence of personal data.
- Do not modify `services/api`, `services/worker`, persistence tables, migrations, or model code in M1.

---

### Task 1: Add the fail-closed source permission contract

**Files:**
- Create: `packages/core/carvalue_core/source_policy.py`
- Reuse: existing source-policy reason codes in `packages/core/carvalue_core/reasons.py`; no new reason code is required by this plan
- Test: `tests/test_source_policy.py`

**Interfaces:**
- Consumes: timezone-aware UTC `datetime`, source metadata supplied by an adapter/import boundary.
- Produces: `SourceType`, `PermissionStatus`, `SourcePolicy`, `PreflightDecision`, and `preflight_automated_source(policy, now_utc)` for later adapters and M2 import orchestration.

- [ ] **Step 1: Write the failing tests for status and required policy metadata**

```python
from datetime import UTC, datetime, timedelta

from carvalue_core.reasons import ReasonCode
from carvalue_core.source_policy import (
    PermissionStatus,
    SourcePolicy,
    SourceType,
    preflight_automated_source,
)


NOW = datetime(2026, 8, 21, 12, tzinfo=UTC)


def policy(**overrides: object) -> SourcePolicy:
    values = {
        "source_id": 1,
        "name": "Authorized fixture feed",
        "source_type": SourceType.API_FEED,
        "origin": "local://authorized-fixture",
        "permission_status": PermissionStatus.APPROVED,
        "permission_basis": "project-owner test authorization",
        "policy_reviewed_at_utc": NOW - timedelta(days=1),
        "policy_review_expires_at_utc": NOW + timedelta(days=30),
        "permitted_fields": frozenset({"year", "mileage_km", "price_cad"}),
        "retention_deadline_utc": NOW + timedelta(days=90),
        "attribution": "Authorized fixture",
        "rate_limit_per_second": 1.0,
        "enabled": True,
    }
    values.update(overrides)
    return SourcePolicy(**values)


def test_unknown_permission_blocks_automated_source() -> None:
    decision = preflight_automated_source(policy(permission_status=PermissionStatus.UNKNOWN), NOW)
    assert decision.allowed is False
    assert decision.reason_code == ReasonCode.SOURCE_PERMISSION_BLOCKED


def test_expired_review_blocks_automated_source() -> None:
    decision = preflight_automated_source(
        policy(policy_review_expires_at_utc=NOW - timedelta(seconds=1)), NOW
    )
    assert decision.allowed is False
    assert decision.reason_code == ReasonCode.SOURCE_POLICY_REVIEW_EXPIRED


def test_approved_current_enabled_source_passes() -> None:
    decision = preflight_automated_source(policy(), NOW)
    assert decision.allowed is True
    assert decision.reason_code is None


def test_disabled_source_blocks_before_permission_check() -> None:
    decision = preflight_automated_source(
        policy(enabled=False, permission_status=PermissionStatus.UNKNOWN), NOW
    )
    assert decision.allowed is False
    assert decision.reason_code == ReasonCode.SOURCE_DISABLED
```

- [ ] **Step 2: Run the focused tests and confirm the expected RED failure**

Run: `pytest tests/test_source_policy.py -v`

Expected: collection fails because `carvalue_core.source_policy` does not exist.

- [ ] **Step 3: Implement the minimal typed policy module**

Define the exact enums and dataclasses:

```python
class SourceType(str, Enum):
    MANUAL_IMPORT = "manual_import"
    API_FEED = "api_feed"
    CRAWLER = "crawler"
    OPEN_DATA = "open_data"


class PermissionStatus(str, Enum):
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
    permitted_fields: frozenset[str]
    retention_deadline_utc: datetime | None
    attribution: str | None
    rate_limit_per_second: float | None
    enabled: bool
    owner_notes: str | None = None


@dataclass(frozen=True)
class PreflightDecision:
    allowed: bool
    reason_code: ReasonCode | None = None


def preflight_automated_source(policy: SourcePolicy, now_utc: datetime) -> PreflightDecision:
    """Return a fail-closed decision for automated source execution."""
```

Check `enabled`, then permission status, then review expiry, then required policy metadata. Return `SOURCE_DISABLED`, `SOURCE_PERMISSION_BLOCKED`, or `SOURCE_POLICY_REVIEW_EXPIRED` as applicable; return `allowed=True` only for an approved, current, complete policy. Do not call the network.

- [ ] **Step 4: Run the focused tests and confirm GREEN**

Run: `pytest tests/test_source_policy.py -v`

Expected: all source-policy tests pass.

- [ ] **Step 5: Commit the isolated contract**

```bash
git add packages/core/carvalue_core/source_policy.py packages/core/carvalue_core/reasons.py tests/test_source_policy.py
git commit -m "feat: add fail-closed source policy contract"
```

### Task 2: Harden deterministic pickup taxonomy resolution

**Files:**
- Modify: `packages/core/carvalue_core/taxonomy.py`
- Test: `tests/test_taxonomy_contract.py`

**Interfaces:**
- Consumes: `TaxonomyNode`, `PickupTaxonomy`, and seeded canonical nodes.
- Produces: unchanged public resolver names `normalize_token`, `resolve_make`, `resolve_model`, `resolve_trim`, and `known_models_for_make`, with aliases normalized consistently.

- [ ] **Step 1: Write failing alias and hierarchy tests**

```python
from carvalue_core.taxonomy import PickupTaxonomy, seed_pickup_taxonomy


def taxonomy() -> PickupTaxonomy:
    return PickupTaxonomy.from_nodes(seed_pickup_taxonomy())


def test_make_aliases_are_case_and_accent_insensitive() -> None:
    values = taxonomy()
    assert values.resolve_make("  CHEVY ") == "chevrolet"
    assert values.resolve_make("FÓRD") == "ford"


def test_model_and_trim_aliases_are_normalized_within_parent() -> None:
    values = taxonomy()
    assert values.resolve_model("ford", " Ranger ") == "ranger"
    assert values.resolve_trim("ranger", " XLT FX4 ") == "xlt"


def test_unknown_parent_or_child_does_not_resolve() -> None:
    values = taxonomy()
    assert values.resolve_model("toyota", "ranger") is None
    assert values.resolve_trim("silverado", "lariat") is None
```

- [ ] **Step 2: Run the taxonomy tests and confirm the alias failure**

Run: `pytest tests/test_taxonomy_contract.py -v`

Expected: the alias tests fail because model/trim aliases currently compare normalized input to unnormalized stored aliases.

- [ ] **Step 3: Implement canonical alias maps without changing public method names**

Normalize every name in `TaxonomyNode.all_names()` before lookup. Keep parent matching on canonical names, return only `canonical_name`, and preserve `None` for unknown values. Do not add fuzzy matching or arbitrary string acceptance.

- [ ] **Step 4: Run focused and existing import tests**

Run: `pytest tests/test_taxonomy_contract.py tests/test_spreadsheet_import.py -v`

Expected: all focused taxonomy/import tests pass.

- [ ] **Step 5: Commit the taxonomy contract**

```bash
git add packages/core/carvalue_core/taxonomy.py tests/test_taxonomy_contract.py
git commit -m "fix: normalize pickup taxonomy aliases consistently"
```

### Task 3: Enforce the normalized listing observation boundary

**Files:**
- Modify: `packages/core/carvalue_core/units.py`
- Modify: `packages/core/carvalue_core/listings.py`
- Test: `tests/test_listing_contract.py`

**Interfaces:**
- Consumes: integer CAD cents, integer kilometres, canonical strings, and timezone-aware datetimes.
- Produces: `ListingObservation` with `observed_at_utc: datetime`, validated non-negative mileage/price/year, canonical non-empty make/model, and no identity/contact/photo fields.

- [ ] **Step 1: Write failing boundary tests**

```python
from datetime import UTC, datetime

import pytest
from carvalue_core.listings import ListingObservation


def valid_observation(**overrides: object) -> ListingObservation:
    values = {
        "source_id": 1,
        "source_record_id": "r-1",
        "make": "ford",
        "model": "ranger",
        "model_year": 2022,
        "mileage_km": 40_000,
        "asking_price_cad_cents": 3_000_000,
        "observed_at_utc": datetime(2026, 8, 21, tzinfo=UTC),
    }
    values.update(overrides)
    return ListingObservation(**values)


def test_observation_requires_utc_timestamp() -> None:
    with pytest.raises(ValueError, match="UTC"):
        valid_observation(observed_at_utc=datetime(2026, 8, 21))


def test_observation_rejects_negative_or_zero_money_and_distance() -> None:
    with pytest.raises(ValueError):
        valid_observation(mileage_km=-1)
    with pytest.raises(ValueError):
        valid_observation(asking_price_cad_cents=0)


def test_observation_has_no_personal_data_fields() -> None:
    observation = valid_observation()
    assert not hasattr(observation, "seller_name")
    assert not hasattr(observation, "phone")
    assert not hasattr(observation, "email")
    assert not hasattr(observation, "photo")
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `pytest tests/test_listing_contract.py -v`

Expected: the naive timestamp and invalid-value tests fail because the current dataclass accepts them.

- [ ] **Step 3: Implement minimal construction validation**

Use `datetime` and an explicit UTC check. Keep `asking_price_cad_cents` as an integer and reject booleans/non-integers, non-positive prices, negative mileage, empty source record IDs, and empty make/model values. Do not silently convert currency or introduce floating-point persistence. Keep optional configuration fields unchanged.

- [ ] **Step 4: Run the focused and persistence tests**

Run: `pytest tests/test_listing_contract.py tests/test_spreadsheet_import.py -v`

Expected: all focused tests pass and existing persistence/schema tests remain green.

- [ ] **Step 5: Commit the normalized boundary**

```bash
git add packages/core/carvalue_core/units.py packages/core/carvalue_core/listings.py tests/test_listing_contract.py
git commit -m "feat: enforce normalized listing observation boundaries"
```

### Task 4: Add sanitized authorized fixture and contract tests

**Files:**
- Create: `tests/fixtures/ford-ranger/valid.csv`
- Create: `tests/fixtures/ford-ranger/README.md`
- Create: `tests/test_contract_fixtures.py`
- Modify: `packages/core/carvalue_core/imports/spreadsheet.py` only for contract defects exposed by the fixture tests.

**Interfaces:**
- Consumes: `preview_import`, `ImportContext`, `PickupTaxonomy`, the M1 source-policy contract, and the normalized `ListingObservation`.
- Produces: a tracked local fixture with only permitted vehicle/listing facts and deterministic contract coverage. No network or database write.

- [ ] **Step 1: Add the fixture metadata and a minimal CSV**

Use only vehicle/listing facts from the user-provided Ford Ranger workbook. The CSV must contain a header such as:

```csv
Year,Mileage,Price,Trim,Drivetrain,Seller Type,Province,Source Record ID,Observed At
2022,40000,30000,XLT,4WD,Dealer,AB,fixture-1,2026-08-21
2021,65000,27000,XL,2WD,Private,AB,fixture-2,2026-08-21
2023,25000,34000,Lariat,4WD,Dealer,AB,fixture-3,2026-08-21
```

Document in `tests/fixtures/ford-ranger/README.md` that the fixture is sanitized, contains no seller identity/contact/photo data, is authorized for local development/testing by the project owner, is not production market data, and must not be used to enable a live adapter.

- [ ] **Step 2: Write the failing fixture contract tests**

```python
from datetime import UTC, datetime
from pathlib import Path

from carvalue_core.imports.spreadsheet import ImportContext, preview_import
from carvalue_core.taxonomy import PickupTaxonomy, seed_pickup_taxonomy


FIXTURE = Path(__file__).parent / "fixtures" / "ford-ranger" / "valid.csv"


def test_authorized_ford_ranger_fixture_normalizes_deterministically() -> None:
    preview = preview_import(
        FIXTURE,
        ImportContext(
            source_id=1,
            default_make="ford",
            default_model="ranger",
            observed_at_fallback=datetime(2026, 8, 21, tzinfo=UTC),
        ),
        PickupTaxonomy.from_nodes(seed_pickup_taxonomy()),
    )
    assert preview.total_rows == 3
    assert len(preview.accepted_observations) == 3
    assert preview.accepted_observations[0].asking_price_cad_cents == 3_000_000
    assert preview.accepted_observations[0].mileage_km == 40_000
    assert preview.accepted_observations[0].observed_at_utc.utcoffset().total_seconds() == 0


def test_required_price_field_disappearance_is_a_contract_failure(tmp_path: Path) -> None:
    broken = tmp_path / "missing-price.csv"
    broken.write_text(FIXTURE.read_text(encoding="utf-8").replace(",Price,", ",Asking Amount,"))
    preview = preview_import(
        broken,
        ImportContext(
            source_id=1,
            default_make="ford",
            default_model="ranger",
            observed_at_fallback=datetime(2026, 8, 21, tzinfo=UTC),
        ),
        PickupTaxonomy.from_nodes(seed_pickup_taxonomy()),
    )
    assert preview.is_committable is False
    assert any(error[0].value == "column_not_found" for error in preview.column_errors)
```

- [ ] **Step 3: Run fixture tests and confirm RED for any contract gap**

Run: `pytest tests/test_contract_fixtures.py -v`

Expected: the tests either pass for already-supported behavior or identify the exact importer/type defect exposed by the new fixture; do not weaken the assertions to obtain GREEN.

- [ ] **Step 4: Implement only the importer changes required by the contract**

Keep header aliases deterministic, use `Decimal` for price parsing, resolve taxonomy through canonical values, normalize timestamps to UTC, and return `ReasonCode.COLUMN_NOT_FOUND` for missing required columns. Do not evaluate spreadsheet formulas, add personal fields, or add a network/provider branch.

- [ ] **Step 5: Run the fixture and import tests**

Run: `pytest tests/test_contract_fixtures.py tests/test_spreadsheet_import.py -v`

Expected: all fixture/import tests pass with no network access.

- [ ] **Step 6: Commit the authorized fixture contract**

```bash
git add tests/fixtures/ford-ranger tests/test_contract_fixtures.py packages/core/carvalue_core/imports/spreadsheet.py
git commit -m "test: add authorized Ford Ranger contract fixture"
```

### Task 5: M1 integration verification and handoff

**Files:**
- Modify: `docs/TECHNICAL-ROADMAP.md` to record M1 evidence only after all gates pass.
- Create or modify: `HANDOFF.md` with the exact next milestone and any residual risks.

**Interfaces:**
- Consumes: all M1 contracts and tests from Tasks 1–4.
- Produces: reproducible M1 verification evidence and a handoff to M2; no source account, credential, scheduler, or production data.

- [ ] **Step 1: Run the full M1 verification set**

Run:

```bash
pytest
ruff check packages/core services tests
bash -n .githooks/versioning.sh .githooks/pre-commit .githooks/prepare-commit-msg
git diff --check
```

Expected: all tests and shell checks pass. Ruff findings in pre-existing API code must be fixed or explicitly recorded before claiming the M0/M1 exit gate; do not hide them with broad `noqa` rules.

- [ ] **Step 2: Inspect tracked content for policy violations**

Run:

```bash
git status --short
git diff --cached --check
rg -n -i "password|token|cookie|phone|email|seller.?name|photo" tests/fixtures packages/core services
```

Expected: no credentials, cookies, personal identity/contact fields, raw crawl content, or generated artifacts are staged. Any intentional test mention of a prohibited field must be an assertion that the field is excluded.

- [ ] **Step 3: Record the M1 result**

Update the roadmap only with observed evidence: test command output, fixture row count, policy preflight cases, and any remaining lint/type/API gaps. Mark M1 complete only if every acceptance criterion in the spec is satisfied; otherwise leave it current and record the exact blocker.

- [ ] **Step 4: Commit the M1 handoff**

```bash
git add docs/TECHNICAL-ROADMAP.md HANDOFF.md
git commit -m "docs: record milestone 1 verification and milestone 2 handoff"
```

## Plan self-review

- Spec coverage: source policy is Task 1; taxonomy is Task 2; units/listing boundary is Task 3; authorized fixtures and field-disappearance contract are Task 4; observability and exit evidence are Task 5.
- Scope check: no network, adapters, persistence migration, model training, API, UI, or admin implementation is included.
- Type consistency: `SourcePolicy`, `PreflightDecision`, `ListingObservation`, `ImportContext`, `PickupTaxonomy`, `ReasonCode`, and all test signatures use the existing Python package names and the interfaces defined above.
- Placeholder scan: no `TODO`, `TBD`, `FIXME`, or unspecified implementation step is required.
- Guardrail check: every source path fails closed unless approved; fixture content is local, sanitized, and rights-documented; all prices, mileage, and timestamps retain explicit units.
