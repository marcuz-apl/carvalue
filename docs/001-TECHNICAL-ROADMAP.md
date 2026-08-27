# CarValue Technical Roadmap

**Status:** Approved working roadmap  
**Scope:** Alberta used-pickup asking-price valuator  
**Last updated:** 2026-08-21

## Delivery rules

- Build as a modular monolith until measured requirements justify a change.
- Keep CAD, kilometres, UTC timestamps, provenance, and uncertainty explicit at boundaries.
- Treat asking prices as asking-price observations, never confirmed sale prices.
- Prefer `Insufficient Data` to fabricated precision.
- Keep data acquisition deny-by-default. No automated source may run without an approved permission record, current policy review, permitted fields, retention, attribution, and rate-limit metadata.
- Every milestone has an exit gate. A later milestone may use synthetic or authorized fixtures, but it may not bypass an unmet rights, privacy, security, or model-quality gate.

## Milestones

### M0 — Foundation hardening

**Purpose:** Make the existing repository foundation reliable enough to extend.

**Work:** package/import boundaries, application configuration, SQLite migration path, typed contracts, lint/type cleanup, test fixtures, and developer commands.

**Depends on:** repository and PRD baseline.

**Exit gate:** focused core tests pass; formatter/linter/type checks pass for changed code; migrations create a fresh database; no secrets/raw crawls/generated artifacts are tracked.

**Current state:** initial core modules and tests exist; API and persistence code still require hardening before this gate is claimed complete.

### M1 — Data rights and contracts (current)

**Purpose:** Define what CarValue may ingest and the source-neutral data shape it is allowed to store or process.

**Work:** source permission metadata, approved-source preflight contract, Alberta pickup taxonomy and aliases, normalized listing observation schema, stable reject/quarantine codes, and sanitized authorized fixtures.

**Depends on:** M0 boundaries; no production provider access required.

**Exit gate:** a source cannot pass automated preflight without current approval; Ford Ranger fixture rows normalize deterministically in CAD/km/UTC; personal seller data and photos have no path into the contract; required-field disappearance produces a stable failure; fixture rights and retention are documented.

**No-go:** no marketplace crawling, login automation, CAPTCHA handling, stealth tooling, or persistence of unlicensed source data.

### M2 — Import and data quality

**Purpose:** Turn rights-confirmed CSV/XLSX or feed records into traceable, deduplicated observations.

**Work:** preview/commit flow, row-level validation, quarantine and rejection reports, provenance, conservative fingerprints, listing upserts, price history, active/inactive lifecycle, WAL/foreign-key checks, and migrations.

**Depends on:** M1 contracts and authorized fixtures.

**Exit gate:** dry-run imports are repeatable; valid rows commit safely when other rows fail; reruns do not duplicate listings; source policy blocks unauthorized automated runs; counters and rejection reasons are observable.

### M3 — Offline valuation proof

**Purpose:** Establish whether permissioned Alberta data supports a useful, honest estimate.

**Work:** centered vehicle-age OLS baseline, CatBoost candidate, chronological train/validation/test split, quantile or conformal 80% intervals, metrics and slices, out-of-distribution refusal, model card, and supported-segment decision.

**Depends on:** M2 data quality and enough rights-confirmed representative data.

**Exit gate:** launch thresholds in `PRD.md` are evaluated on untouched time-based data; interval coverage and width are reported; no supported segment has a hidden material regression; model artifact metadata and hash are reproducible.

**No-go:** no production promotion from training completion; no model trained on data whose licence does not permit that use.

### M4 — Valuation API

**Purpose:** Expose a stable, validated valuation contract without requiring visitor accounts.

**Work:** FastAPI request/response schemas, taxonomy-backed selections, input bounds, active-model loading, evidence result formatting, refusal responses, valuation date/freshness/comparables/confidence/disclaimer fields, and privacy-minimized event metadata.

**Depends on:** M3 promoted model and M0 security/configuration foundations.

**Exit gate:** PRD visitor acceptance scenarios pass through API tests; unsupported and sparse inputs do not receive fabricated point estimates; response performance is measured.

### M5 — Admin and workers

**Purpose:** Operate imports, source runs, datasets, and models safely.

**Work:** authenticated admin sessions, CSRF/rate limiting, source and schedule management, database leases, bounded retries, run counters, quality review, dataset snapshots, model registry, explicit promotion/rollback, and append-only audit events.

**Depends on:** M2, M3, and M4 contracts.

**Exit gate:** admin authorization and mutation audit scenarios pass; unauthorized/expired sources are blocked; promotion and rollback are explicit and reversible; backup/restore includes the active model reference.

### M6 — Public web experience

**Purpose:** Provide the visitor-facing Alberta pickup valuation journey.

**Work:** Next.js form, accessible controls, responsive result page, confidence/refusal states, disclaimer and freshness presentation, keyboard flow, feedback control, privacy notice, and consent behavior where required.

**Depends on:** M4 API and M5 operational observability.

**Exit gate:** visitor happy path, invalid input, insufficient data, and unsupported vehicle flows pass E2E and accessibility checks; no identity is required for valuation.

### M7 — Launch hardening

**Purpose:** Make the MVP supportable and safe to release.

**Work:** threat model, privacy review, dependency/security audit, security headers, structured logs, retention jobs, backups and restore drill, deployment smoke tests, latency/error/freshness monitoring, and operator runbooks.

**Depends on:** M4–M6 and an approved repeatable data source.

**Exit gate:** PRD launch gates and acceptance scenarios are evidenced; legal/source review is current; production rollback and restore procedures are tested.

### M8 — Coverage expansion

**Purpose:** Expand only where evidence supports the product claim.

**Work:** additional pickup families, configuration coverage, regions, dealer/private representation, consented outcomes, and only later non-pickup segments.

**Depends on:** M7 plus per-segment data, accuracy, calibration, privacy, and source-rights gates.

**Exit gate:** each new segment has its own coverage decision, slice metrics, refusal policy, provenance, and rollback path.

### M9 — Full Alberta Multi-Category Expansion (Complete)

**Purpose:** Deliver full multi-category vehicle coverage (SUVs, Crossovers, Sedans, Coupes, Vans, Hatchbacks) across Alberta.

**Work:** canonical multi-category taxonomy nodes, category-filtered model queries, multi-category database seeding, API category serialization, UI category badges and cascading selectors, and slice regression gate tests.

**Depends on:** M8 coverage expansion foundations and real Alberta dataset.

**Exit gate:** multi-category taxonomy resolution and category slice evaluation pass unit/integration tests; web UI supports cascading category selection; 90/90 tests pass.

## Current execution order

1. Complete Milestones M0 through M9 (All Done).
2. Production operations and live monitoring.

## Decision records

Material changes to scope, source rights, model promotion, storage architecture, or privacy assumptions belong in `docs/adr/` and must update this roadmap and `PRD.md` together.
