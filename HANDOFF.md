# Project Handoff

Updated: 2026-08-24 16:30 UTC  
Branch: master  
Commit: All Milestones (M0–M8) Completed  
Status: ALL MILESTONES COMPLETE — READY FOR RELEASE  

## Summary

The entire Technical Roadmap (**Milestones M0 through M8**) has been implemented, tested, and documented for the CarValue Alberta Used Pickup Valuator according to `PRD.md` and repository guardrails.

---

## Complete Milestone Index

- **M0 — Foundation Hardening:**
  - Package structure: `packages/core/carvalue_core`, `services/api/carvalue_api`, `services/worker/carvalue_worker`.
  - SQLite migration runner (`carvalue_api.migrations`) and CLI entry point (`carvalue init-db`).
  - Unit conversion and rounding in `carvalue_core.units` (CAD integer cents, km integers, nearest $100 CAD rounding).

- **M1 — Data Rights & Taxonomy Contracts:**
  - Deny-by-default source policy model (`SourcePolicy`).
  - Alberta pickup taxonomy system of record with aliases (`carvalue_core.taxonomy`).
  - Strict normalized listing observation contract (`ListingObservation`).
  - Rejection and quarantine reason codes (`ReasonCode`).

- **M2 — Import & Data Quality Pipeline:**
  - Spreadsheet import preview and commit (`carvalue_core.imports.spreadsheet`).
  - Observation upserting, deduplication, price history appending, and active/inactive lifecycle (`carvalue_core.persistence`).
  - Cross-source collision detection without merging (`tests/test_import_data_quality.py`).

- **M3 — Offline Valuation Proof & Model Governance:**
  - `ValuationModel` base with SHA256 checksumming and serialization (`carvalue_core.models`).
  - Centered-age Statsmodels `OLSBaseline` with 80% prediction intervals.
  - Nonlinear `CatBoostCandidate` with categorical features and 80% prediction intervals.
  - `chronological_split` eliminating temporal data leakage.
  - `compute_metrics` calculating MAE in CAD, MdAPE, RMSE, sample count, coverage, and segment slices.
  - `evaluate_prediction` refusing out-of-distribution or sparse (<4 comparables) inputs.

- **M4 — Valuation API:**
  - Lifespan handler (`carvalue_api.lifespan`).
  - `POST /v1/valuations`: active model lookup, comparable counting, freshness calculation, refusal evaluation, rounded CAD estimate, 80% interval, and privacy-minimized visitor telemetry (`ValuationEvent`).
  - `GET /v1/taxonomy`: returns canonical Alberta pickup taxonomy hierarchy.

- **M5 — Admin and Workers:**
  - PBKDF2-HMAC-SHA256 password hashing, 12-hour session tokens, CSRF tokens, and append-only `AuditEvent` logging (`carvalue_core.security`).
  - Background worker engine in `carvalue_worker.engine`: `SourcePreflightChecker`, `SourceLeaseManager`, and `WorkerJobRunner`.
  - Admin API endpoints in `carvalue_api`: session cookies, CSRF defense, `POST /admin/login`, `POST /admin/logout`, `GET /admin/me`, `POST /admin/models/{id}/promote`, `POST /admin/models/{id}/rollback`, `POST /admin/dataset-snapshots`, `POST /admin/data-quality/{id}/resolve`, and `POST /admin/sources/{id}/toggle`.

- **M6 — Public Web Experience:**
  - Next.js 14 + TypeScript frontend in `apps/web`.
  - Vanilla CSS design system with rich Alberta slate/glacier dark mode aesthetics (`globals.css`).
  - Cascading form for vehicle specs (`ValuationForm.tsx`).
  - Asking-price estimate card with 80% prediction interval bar, confidence badge, live comparable count, data freshness, and legal disclaimer (`ValuationResult.tsx`).
  - Explainable refusal card for insufficient data (`RefusalCard.tsx`).
  - Methodology and Canadian privacy compliance pages (`methodology/page.tsx`, `privacy/page.tsx`).

- **M7 — Launch Hardening:**
  - Defense-in-depth HTTP security headers middleware (`nosniff`, `DENY` framing, CSP, Referrer-Policy).
  - System health and market data freshness monitoring (`GET /v1/system/status`).
  - Point-in-time SQLite online backup & atomic restore maintenance engine (`carvalue_api.maintenance`).
  - Automated data retention purge (`purge_expired_retention`) for raw crawl content and expired sessions.
  - Formal security threat model (`docs/THREAT-MODEL.md`).
  - Alberta PIPA / Canadian PIPEDA statutory privacy review (`docs/PRIVACY-REVIEW.md`).
  - Operator runbook (`docs/RUNBOOK.md`).

- **M8 — Coverage Expansion:**
  - Heavy-Duty pickup taxonomy: Super Duty F-250/F-350, Silverado 2500HD/3500HD, Sierra 2500HD/3500HD, Ram 2500/3500, Tundra, Titan (`carvalue_core.taxonomy`).
  - Alberta regional sub-market segmentation (Calgary, Edmonton, Red Deer, Lethbridge, Medicine Hat, Fort McMurray, Grande Prairie, Rural Alberta).
  - `SegmentRegressionGate`: prevents promotion if any supported segment regresses $>8\%$ MAE.
  - Anonymous visitor feedback endpoint (`POST /v1/valuations/feedback`).
  - Architectural decision record (`docs/adr/0002-coverage-expansion-governance.md`).
