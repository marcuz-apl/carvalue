# Project Handoff

Updated: 2026-08-24 11:00 UTC  
Branch: master  
Commit: Milestone M5 Completed  
Status: ready for review  

## Summary

Milestones **M0 (Foundation hardening)**, **M1 (Data rights and contracts)**, **M2 (Import and data quality)**, **M3 (Offline valuation proof & model governance)**, **M4 (Valuation API)**, and **M5 (Admin and workers)** have been implemented and verified. All 71 tests pass across the entire repository.

## Completed Milestones

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

- **M3 — Offline Valuation Proof & Model Governance:**
  - Standard `ValuationModel` base with SHA256 checksumming and serialization (`carvalue_core.models.ValuationModel`).
  - Centered-age Statsmodels `OLSBaseline` model with 80% prediction intervals (PRD FR-ML-01).
  - Nonlinear `CatBoostCandidate` model with categorical feature handling and 80% prediction intervals (PRD FR-ML-02, FR-ML-03).
  - `chronological_split` to eliminate temporal data leakage (PRD FR-ML-06, FR-ML-07).
  - `compute_metrics` calculating MAE in CAD, MdAPE, RMSE, sample count, coverage, and segment slices (PRD FR-ML-08).
  - `evaluate_prediction` refusing out-of-distribution, sparse (<4 comparables), or stale data (PRD FR-ML-10).

- **M4 — Valuation API:**
  - Async lifespan handler (`carvalue_api.lifespan`).
  - `POST /v1/valuations`: active model lookup, comparable counting, freshness calculation, refusal evaluation, rounded CAD estimate, 80% interval, and privacy-minimized visitor telemetry (`ValuationEvent`).
  - `GET /v1/taxonomy`: returns canonical Alberta pickup taxonomy hierarchy.

- **M5 — Admin and Workers:**
  - Security primitives in `carvalue_core.security`: PBKDF2-HMAC-SHA256 password hashing, cryptographically secure 12-hour sessions, CSRF token hashing, and append-only `AuditEvent` logging.
  - Background worker engine in `carvalue_worker.engine`: `SourcePreflightChecker` (fail closed on unapproved, disabled, or expired policy review sources), `SourceLeaseManager` (exclusive SQLite-safe `CrawlRun` leases), and `WorkerJobRunner` with run counters.
  - Admin API endpoints in `carvalue_api`: session auth cookie middleware, CSRF defense, `POST /admin/login`, `POST /admin/logout`, `GET /admin/me`, `POST /admin/models/{id}/promote`, `POST /admin/models/{id}/rollback`, `POST /admin/dataset-snapshots`, `POST /admin/data-quality/{id}/resolve`, and `POST /admin/sources/{id}/toggle`.

## Test Results

- Total tests: **71 passed** (100%) in 98s.
  - `tests/test_admin_api.py`: 8 passed
  - `tests/test_admin_security.py`: 6 passed
  - `tests/test_worker_engine.py`: 3 passed
  - `tests/test_valuation_api.py`: 7 passed
  - `tests/test_valuation_models.py`: 6 passed
  - `tests/test_spreadsheet_import.py`: 2 passed
  - `tests/test_source_policy.py`: 14 passed
  - `tests/test_normalized_contract.py`: 5 passed
  - `tests/test_migrations.py`: 3 passed
  - `tests/test_import_data_quality.py`: 6 passed
  - `tests/test_ford_ranger_fixture.py`: 3 passed
  - `tests/test_cli_init_db.py`: 2 passed
  - `tests/test_alfazen_versioning.py`: 6 passed

## Next Milestone: M6 (Public Web Experience)

The next planned milestone is **Milestone M6 (Public web experience)**:
- Next.js 14 public visitor UI in `apps/web`.
- Accessible Alberta pickup valuation form (make, model, year, mileage, trim, drivetrain, seller type).
- Responsive valuation results display with rounded CAD estimate, 80% prediction interval bar, confidence badge, comparables count, freshness, and mandatory disclaimer.
- Admin UI for model promotion/rollback, dataset snapshots, source toggling, and data quality issue reviews.
