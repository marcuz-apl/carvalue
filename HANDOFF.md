# Project Handoff

Updated: 2026-08-24 10:45 UTC  
Branch: master  
Commit: 511637e (HEAD -> master, origin/master, origin/HEAD)  
Status: ready for review  

## Summary

Milestones **M0 (Foundation hardening)**, **M1 (Data rights and contracts)**, **M2 (Import and data quality)**, **M3 (Offline valuation proof & model governance)**, and **M4 (Valuation API)** have been implemented and verified. All 54 tests pass across the entire repository with 100% compliance on linting (`ruff`), formatting, and static typing (`mypy`).

## Completed

- **M0 — Foundation Hardening:**
  - Package & import boundaries established: `packages/core/carvalue_core`, `services/api/carvalue_api`, `services/worker/carvalue_worker`.
  - SQLite database migration runner (`services/api/carvalue_api/migrations/__init__.py`) and CLI entry point (`carvalue init-db`).
  - Unit conversion and rounding standards in `carvalue_core.units` (CAD integer cents, km integers, nearest $100 CAD rounding).

- **M1 — Data Rights & Taxonomy Contracts:**
  - Deny-by-default source policy rules (`carvalue_core.persistence.SourcePolicy`).
  - Alberta pickup taxonomy system of record with aliases (`carvalue_core.taxonomy`).
  - Strict normalized listing observation contract (`carvalue_core.listings.ListingObservation`).
  - Rejection and quarantine reason codes (`carvalue_core.reasons.ReasonCode`).

- **M2 — Import & Data Quality Pipeline:**
  - Spreadsheet import dry-run preview and commit (`carvalue_core.imports.spreadsheet`).
  - Listing observation upserting, deduplication, price history appending, and active/inactive lifecycle (`carvalue_core.persistence`).
  - Cross-source collision detection without merging (`tests/test_import_data_quality.py`).
  - Data quality issue reporting and quarantine tracking.

- **M3 — Offline Valuation Proof & Model Governance:**
  - Base `ValuationModel` class with serialization (`.save()`, `.load()`) and SHA256 checksum verification (`carvalue_core.models.py`).
  - Centered vehicle-age `OLSBaseline` with Statsmodels OLS (PRD FR-ML-01).
  - Nonlinear `CatBoostCandidate` with categorical trim/drivetrain/seller-type features and 80% prediction intervals via quantile regressors (PRD FR-ML-02, FR-ML-03).
  - Chronological train/val/test split (`chronological_split`) preventing temporal data leakage (PRD FR-ML-06, FR-ML-07).
  - Comprehensive metric computation (`compute_metrics`): MAE (CAD), MdAPE, RMSE, sample count, empirical 80% interval coverage, mean relative width, and segment slices (PRD FR-ML-08).
  - Refusal decision rules (`evaluate_prediction`, `decide_confidence`): refuses sparse segments (<4 comparables), out-of-distribution inputs, and stale data (PRD FR-ML-10).

- **M4 — Valuation API:**
  - FastAPI application lifespan context (`services/api/carvalue_api/__init__.py`).
  - Public `POST /v1/valuations` endpoint loading active `ModelVersion` artifact from SQLite, querying comparables and data freshness, running prediction, applying refusal rules, and returning rounded CAD asking-price estimate, 80% interval, confidence label, freshness, and disclaimer.
  - Public `GET /v1/taxonomy` endpoint returning canonical taxonomy tree.
  - Privacy-minimized telemetry logging to `ValuationEvent` (recording latency ms, device class, inputs, confidence label; no PII) (PRD FR-OBS-01).
  - Comprehensive M4 test suite (`tests/test_valuation_api.py`) verifying happy path, out-of-distribution refusal, sparse comparables refusal, unsupported vehicle refusal, input validation, and response latency.

## Working tree

- Modified:
  - `.gitignore` (added `catboost_info/`)
  - `packages/core/carvalue_core/__init__.py`
  - `packages/core/carvalue_core/confidence.py`
  - `packages/core/carvalue_core/imports/spreadsheet.py`
  - `packages/core/carvalue_core/listings.py`
  - `packages/core/carvalue_core/persistence.py`
  - `packages/core/carvalue_core/reasons.py`
  - `packages/core/carvalue_core/taxonomy.py`
  - `packages/core/carvalue_core/units.py`
  - `pyproject.toml`
  - `services/api/carvalue_api/__init__.py`
  - `services/api/carvalue_api/cli.py`
  - `services/api/carvalue_api/migrations/__init__.py`
  - `services/worker/carvalue_worker/__init__.py`
  - `tests/test_cli_init_db.py`
  - `tests/test_migrations.py`
  - `tests/test_spreadsheet_import.py`
- Untracked:
  - `packages/core/carvalue_core/models.py`
  - `tests/test_import_data_quality.py`
  - `tests/test_valuation_api.py`
  - `tests/test_valuation_models.py`

## Checks

- `/home/zenusr/.venv_carvalue/bin/pytest -v` — PASS (54 passed in 55s)
- `/home/zenusr/.venv_carvalue/bin/ruff check .` — PASS (All checks passed)
- `/home/zenusr/.venv_carvalue/bin/ruff format --check .` — PASS (All 35 files formatted)
- `/home/zenusr/.venv_carvalue/bin/mypy packages services` — PASS (Success: no issues found in 14 source files)

## Decisions and context

- Python virtual environment is located on native ext4 filesystem at `/home/zenusr/.venv_carvalue` to avoid 9p Windows mount limitations.
- All persisted money values use integer cents (`asking_price_cad_cents`).
- All mileage values use integer non-negative kilometres (`mileage_km`).
- CatBoost categorical feature series are aligned to DataFrame index before model fitting and prediction.
- API inputs outside supported Alberta taxonomy or training domain bounds return `confidence_label="insufficient_data"` with estimate CAD 0 rather than fabricated precision.

## Blockers

- None.

## Next action

1. Proceed to **Milestone M5 (Admin and workers)**:
   - Admin authentication & CSRF session cookies.
   - Dataset snapshotting and model promotion/rollback commands.
   - Background worker leases, rate limits, and run counters.
2. Proceed to **Milestone M6 (Public web experience)**:
   - Next.js 14 frontend in `apps/web`.
   - Accessible valuation form and responsive price-estimate results display.
