# CarValue Alberta Pickup Valuator — Product Requirements Document

**Status:** Draft for implementation  
**Version:** 1.0  
**Market:** Alberta, Canada  
**Initial vehicle segment:** Used pickup trucks  
**Currency and units:** CAD and kilometres

## 1. Product summary

CarValue is a web application that estimates the current Alberta asking-price range for a used pickup truck. A visitor supplies a small set of vehicle facts and receives an explainable estimate, a confidence range, the number and freshness of comparable listings, and a clear statement that the result is an estimate rather than an appraisal or guaranteed sale price.

An authenticated administrator manages approved data sources, imports or schedules listing collection, reviews data quality, trains and promotes valuation models, and monitors service usage.

The MVP proves one thesis: sufficiently fresh, permissioned Alberta pickup-listing data can produce a useful and honest valuation for common make/model/trim combinations. Sedans, SUVs/MPVs, nationwide coverage, dealer inventory tools, and transactional features are later work.

## 2. Problem and opportunity

Alberta pickup buyers and sellers must compare many listings with different years, mileage, trims, cab/box configurations, drivetrains, locations, and seller types. A simple two-variable regression is understandable, but it can confuse trim and configuration differences with depreciation and gives no reliable uncertainty estimate.

The supplied Ford Ranger example is a useful baseline but not a production dataset:

- 32 current observations covering model years 2019–2023;
- only `Year`, `Mileage`, and asking `Price`;
- zero exact duplicate rows in the current workbook;
- no source date, Alberta location, trim/configuration, seller type, condition, or sold-price outcome;
- the accompanying legacy regression report was produced from the earlier 33-row version, before duplicate removal, and has no held-out or time-based validation.

## 3. Target users

### Primary user

An Alberta resident considering buying or privately selling a used pickup, who wants a quick evidence-based price range without building a spreadsheet.

### Secondary user

The service administrator, who needs safe ingestion, scheduling, data-quality review, model governance, and operational visibility.

## 4. Goals and success measures

### MVP goals

1. Return an explainable Alberta pickup valuation in under 3 seconds for a supported vehicle after submission.
2. Show a range and evidence quality, not false precision.
3. Maintain traceable, permissioned, deduplicated listing data.
4. Allow an administrator to import/collect data, inspect failures, train a candidate model, compare it with the active model, and explicitly promote it.
5. Collect privacy-minimized service analytics and operational logs.

### Launch gates

- At least 1,000 clean, active or recently observed Alberta pickup listings overall.
- At least 50 useful comparables for each make/model family exposed as “supported”; sparse combinations must be labelled low-confidence or unavailable.
- Time-based holdout median absolute percentage error (MdAPE) ≤ 12% overall and ≤ 15% for every supported high-volume make/model family.
- 80% empirical coverage for the displayed 80% prediction interval, within ±5 percentage points overall.
- No candidate is promoted when it performs materially worse than the active model on overall accuracy, a supported high-volume segment, or interval calibration.
- 95th-percentile cached valuation response ≤ 3 seconds.
- 100% of production listing records have source provenance and collection timestamps.
- 100% of enabled automated sources have recorded permission status and a current policy review.

### Product learning metrics

- valuation completion rate;
- repeat valuation rate within 30 days, using consented/pseudonymous analytics;
- percentage of results with medium or high evidence quality;
- visitor feedback: “useful / not useful” and optional expected transaction price;
- model error by make/model, model year, price band, seller type, and region when outcome data becomes available.

Page views alone are not a success metric.

## 5. Scope

### MVP in scope

- Alberta pickup trucks only;
- public valuation form and results page;
- supported make/model/trim selection from normalized reference data;
- input fields: model year, odometer kilometres, trim, drivetrain, and seller type;
- recommended additional configuration fields when data permits: cab style and box length;
- estimated fair asking price, 80% prediction interval, comparable count, data freshness, confidence/evidence label, and top value drivers;
- dealer/private adjustment learned from data when adequately represented—never a fixed unexplained subtraction;
- admin authentication and role protection;
- CSV/XLSX import with preview, validation, rejection report, and provenance;
- permission-gated scheduled collection for approved sources;
- source/job/run management, data-quality dashboard, model training/evaluation/promotion, and audit log;
- privacy-minimized visitor event log;
- SQLite database, backups, and documented migration path.

### Explicitly out of scope for MVP

- sedans, SUVs, MPVs, motorcycles, commercial/heavy trucks, or markets outside Alberta;
- guaranteed appraisal, lending value, insurance value, trade-in offer, or exact sale-price prediction;
- vehicle-history lookup, VIN decoding unless a licensed source is added, financing, payments, messaging, accounts for public visitors, or listings marketplace;
- collecting personal seller contact details or listing photos;
- bypassing authentication, CAPTCHAs, bot controls, rate limits, paywalls, robots rules, or source terms;
- autonomous model promotion;
- generative-AI/LLM extraction in the production hot path.

## 6. Core user journeys

### Visitor valuation

1. Visitor selects make, model, year, trim, drivetrain, seller type, and enters odometer kilometres; cab/box are requested where applicable.
2. The system validates realistic ranges and presents unit/currency labels.
3. The system resolves a supported segment, loads the active model, and predicts a point estimate and interval.
4. The results page displays:
   - rounded fair asking-price estimate (nearest CAD 100);
   - 80% expected asking-price range;
   - confidence label: High, Medium, Low, or Insufficient Data;
   - comparable listing count and median age;
   - material drivers such as year, mileage, trim, or drivetrain;
   - “asking prices are not confirmed transaction prices” and valuation timestamp;
   - feedback control.
5. If inputs are out of distribution or evidence is insufficient, the system does not invent precision; it returns a broad low-confidence result or “not enough data.”

### Administrator data update

1. Admin creates or selects an approved source or manual import.
2. For automated sources, the system verifies that permission status is `approved`, the policy review is current, and the source is enabled.
3. Admin starts a run immediately or creates a schedule.
4. A background worker collects raw observations, stores run metadata, validates and normalizes records, and performs deterministic deduplication.
5. Admin sees totals for fetched, accepted, updated, duplicate, quarantined, rejected, and failed records, with a downloadable rejection report.

### Model lifecycle

1. Admin chooses an eligible snapshot and starts training.
2. The worker creates a time-based train/validation/test split and fits baseline and candidate models.
3. Admin reviews accuracy, interval calibration, segment metrics, dataset/version metadata, and feature importance.
4. Promotion is an explicit audited action; rollback to a previous model remains available.

## 7. Functional requirements

### Public application

- **FR-PUB-01:** Only valid, normalized selections are submitted; arbitrary model/trim strings are not accepted.
- **FR-PUB-02:** Mileage must be in kilometres and bounded by configurable plausible limits.
- **FR-PUB-03:** Results must identify valuation date, CAD currency, interval level, confidence, comparables, and data freshness.
- **FR-PUB-04:** Unsupported or out-of-distribution requests return a useful explanation and no misleading point estimate.
- **FR-PUB-05:** The UI is responsive, keyboard operable, and meets WCAG 2.2 AA for core flows.
- **FR-PUB-06:** No login or personal information is required for a valuation.

### Data ingestion

- **FR-DATA-01:** Every source records name, type, base URL/file origin, permission basis, policy/robots review timestamp, rate limit, enabled state, and owner notes.
- **FR-DATA-02:** Automated collection is blocked unless the source is explicitly approved and current; `unknown`, `denied`, and expired reviews cannot run.
- **FR-DATA-03:** Collect only fields necessary for valuation; exclude seller name, phone, email, free-form personal details, and photos.
- **FR-DATA-04:** Preserve source listing ID/URL where permitted, first/last-seen timestamps, fetched timestamp, source, raw-content checksum, parser version, and normalized record.
- **FR-DATA-05:** Upsert repeated observations and preserve price history rather than duplicating a listing.
- **FR-DATA-06:** Deduplicate by source/source ID first, then canonical URL, then a conservative fingerprint of vehicle and dealer/location attributes.
- **FR-DATA-07:** Records with missing price/year/mileage, non-CAD/ambiguous price, impossible values, non-Alberta location, or uncertain vehicle identity are rejected or quarantined with reason codes.
- **FR-DATA-08:** A parser contract test using saved, authorized fixtures must run before deployment.
- **FR-DATA-09:** A source adapter failure cannot corrupt previously accepted data and must be retryable/idempotent.
- **FR-DATA-10:** Imports support CSV and XLSX, column mapping, dry-run preview, and row-level errors.

### Admin and scheduling

- **FR-ADM-01:** Admin routes require authenticated sessions, strong password hashing, CSRF protection, secure cookies, rate limiting, and configurable session expiry.
- **FR-ADM-02:** Admin can create, pause, resume, run, and inspect schedules and jobs.
- **FR-ADM-03:** A job state is one of queued, running, succeeded, partially_succeeded, failed, or cancelled.
- **FR-ADM-04:** Concurrent runs for the same source are prevented by a database-backed lease.
- **FR-ADM-05:** Mutating admin actions are written to an immutable application audit trail with actor, time, action, target, and outcome; secrets and raw passwords are never logged.
- **FR-ADM-06:** Source credentials, if later required, come from environment/secret storage, not SQLite or source control.

### Valuation and model governance

- **FR-ML-01:** The current two-feature OLS model is retained as a transparent benchmark, with vehicle age centred to the valuation date rather than a large raw-year intercept.
- **FR-ML-02:** The recommended production candidate is CatBoost regression because it handles nonlinear mileage/age effects, interactions, missing values, and categorical trim/configuration with limited preprocessing.
- **FR-ML-03:** Train two quantile models (10th and 90th percentile), or an empirically calibrated conformal interval around the point model, to produce the 80% interval.
- **FR-ML-04:** The MVP core features are vehicle age, odometer kilometres, trim, drivetrain, and seller type. Add cab style, box length, region, and listing age only when coverage and quality are adequate.
- **FR-ML-05:** Price is modelled in log space when validation shows improved relative-error stability; output is transformed back to CAD and bias-corrected/calibrated.
- **FR-ML-06:** The split is chronological by collection/listing date. Random-only splits are prohibited because they overstate performance under market drift.
- **FR-ML-07:** Hyperparameter tuning occurs only inside training data; the final time holdout remains untouched until evaluation.
- **FR-ML-08:** Report MAE (CAD), MdAPE, RMSE, interval coverage/width, sample count, and error slices. R² is secondary, not the launch criterion.
- **FR-ML-09:** Candidate artifacts contain code version, data snapshot, feature schema, metrics, training time, and model hash.
- **FR-ML-10:** Predictions are refused or downgraded when a category is unseen, inputs fall outside training bounds, the segment is sparse, the model/data is stale, or interval width exceeds a configured threshold.
- **FR-ML-11:** No fixed “private sale = dealer price minus CAD 3,000” rule is used unless supported and monitored from representative data.

### Visitor analytics and privacy

- **FR-OBS-01:** Log event type, timestamp, request/correlation ID, coarse device class, coarse region when consent and policy permit, latency, response status, model version, confidence label, and pseudonymous rotating visitor ID.
- **FR-OBS-02:** Do not store raw IP addresses beyond short-lived security logs; do not fingerprint visitors.
- **FR-OBS-03:** Separate security/operational logs from product analytics and define retention periods (default: security 30 days, analytics 13 months, audit records 24 months, subject to legal review).
- **FR-OBS-04:** Provide a privacy notice and consent controls where required. Production policy must be reviewed for Alberta’s PIPA and any other applicable Canadian privacy obligations before launch.

## 8. Data model (SQLite)

Minimum tables:

- `sources`: source policy, permission status, review dates, adapter and rate limits;
- `crawl_schedules`: schedule expression/time zone, source, enabled state, next run;
- `crawl_runs`: state, counters, timestamps, error summary, parser version;
- `raw_observations`: optional compressed response/body reference or checksum, fetched time, HTTP metadata, retention expiry;
- `listings`: normalized vehicle/listing identity, provenance, first/last seen, active state;
- `listing_price_history`: listing, observed time, asking price CAD;
- `vehicle_taxonomy`: make/model/trim/configuration aliases and canonical values;
- `data_quality_issues`: record/run, reason, status, reviewer;
- `dataset_snapshots`: immutable training query/version and row counts;
- `model_versions`: algorithm, artifact path, feature schema, metrics, status;
- `valuation_events`: privacy-minimized inputs/output metadata and feedback, not personal identity;
- `admin_users`, `admin_sessions`, and `audit_events`.

SQLite requirements:

- WAL mode, foreign keys enabled, busy timeout, bounded worker concurrency, migrations, and transactions;
- money stored as integer cents and timestamps as UTC ISO-8601 values;
- scheduled encrypted backups with restore drills;
- raw content retention shorter than normalized factual observations where licensing permits;
- migrate to PostgreSQL when sustained write concurrency, multiple workers/hosts, or database size/operational contention exceeds the documented threshold.

## 9. Recommended architecture

Use a modular monolith for the MVP:

- **Web/UI:** Next.js + TypeScript, server-rendered public pages, accessible component library, responsive design;
- **Application API:** FastAPI + Pydantic + SQLAlchemy/Alembic, keeping validation/training close to the Python ML ecosystem;
- **Worker/scheduler:** a separate Python worker process using APScheduler with persistent SQLite job/run records and database leases;
- **Permitted browser collection:** Playwright, using stable locators and deterministic schemas. It supports Node.js, Python, Java, and .NET, so it does not lock the project to one language;
- **Optional discovery/extraction aid:** self-hosted Crawl4AI for permissioned sources with irregular pages; accepted records still pass deterministic validation. Firecrawl is not required for the free/self-hosted MVP and must not become a policy-bypass layer;
- **ML:** pandas/polars, scikit-learn-compatible pipelines, CatBoost, Statsmodels baseline, joblib/model artifact store;
- **Storage:** SQLite plus filesystem artifacts/backups for a single-host deployment.

The crawler is an adapter boundary. Each source owns URL discovery, fetch, parse, normalize, policy metadata, rate limiting, and fixtures. The rest of the application consumes a source-neutral listing schema.

## 10. Source acquisition and compliance gate

The named marketplaces cannot be assumed crawlable merely because pages are public. At the time this PRD was prepared, [AutoTrader.ca’s terms](https://www.autotrader.ca/Cms/TermsConditions/) state that automated access and collection/indexing are prohibited. [CarGurus’ terms](https://www.cargurus.com/about/terms-of-use) prohibit systematic extraction and scraping except within their stated conditions. Written permission, a licensed feed/API, or counsel-approved use is therefore a prerequisite before enabling those adapters.

Preferred source order:

1. licensed marketplace/dealer feeds or written partner permission;
2. direct dealer inventory feeds with permission;
3. government/open datasets whose licence permits this use;
4. administrator or user-contributed CSV/XLSX data with documented rights;
5. permitted public pages only after terms, robots directives, copyright/database rights, privacy, attribution, retention, and rate limits are reviewed.

The source review must be repeated at least every 90 days and immediately on a relevant policy change. The product must not employ stealth, proxy rotation, CAPTCHA solving, login automation, or other access-control evasion.

Technology references: [Playwright browser support](https://playwright.dev/docs/browsers) and [Crawl4AI documentation](https://docs.crawl4ai.com/).

## 11. Non-functional requirements

- **Security:** OWASP-aligned input handling, dependency scanning, least privilege, security headers, admin rate limiting, secret scanning, and no secrets in logs/source.
- **Reliability:** idempotent runs, retry with capped exponential backoff and jitter, per-source circuit breaker, graceful restart, backup and restore documentation.
- **Performance:** public P95 ≤ 3 seconds cached and ≤ 5 seconds uncached; admin pages P95 ≤ 5 seconds for normal datasets; collection/training always asynchronous.
- **Accessibility:** WCAG 2.2 AA for public valuation and essential admin operations.
- **Observability:** structured logs, request/job correlation IDs, job duration/success/record counters, prediction latency, error rate, data freshness, and drift alerts.
- **Maintainability:** typed boundaries, versioned migrations/schemas/models, source adapter contract tests, unit/integration/E2E coverage for critical paths.
- **Reproducibility:** a model can be regenerated from its immutable snapshot and recorded code/config version.

## 12. Acceptance scenarios

1. Given a supported Alberta Ford Ranger with valid inputs, the visitor sees a rounded CAD estimate, 80% interval, freshness, comparable count, confidence, and disclaimer.
2. Given implausible mileage or an unsupported year/model, submission is rejected or returns Insufficient Data without a fabricated estimate.
3. Given an exact repeated listing observation, ingestion updates last-seen/price history and does not create a duplicate listing.
4. Given a source with permission `unknown`, `denied`, or expired review, a scheduled/manual automated run is blocked and audited.
5. Given a parser fixture whose required price field disappears, its contract test fails and the adapter is not deployed.
6. Given a partially failing run, valid rows commit safely, failures are quarantined with reasons, and rerun does not duplicate data.
7. Given a candidate whose overall metric improves but a supported high-volume segment materially regresses, promotion is blocked pending explicit review/override with reason.
8. Given a model outside its training domain, the API returns low confidence or insufficient data.
9. Given an unauthenticated request to an admin route, access is denied and no sensitive details are exposed.
10. Given a backup, the documented restore procedure recreates a working database and active model reference in a clean environment.

## 13. Delivery phases

### Phase 0 — Feasibility and permission

- obtain at least one legally usable data source;
- define the normalized pickup taxonomy and import contract;
- import and quality-profile the Ford Ranger example;
- establish baseline metrics and a data-volume plan.

**Exit:** written source permission/licence or a clearly licensed dataset, plus enough representative Alberta data to test the thesis. No automated marketplace crawling begins without this gate.

### Phase 1 — Offline valuation proof

- build validation/deduplication, snapshotting, OLS baseline, CatBoost candidate, time-based evaluation, and interval calibration;
- publish a model card and determine supported segments.

**Exit:** launch accuracy/calibration gates met for at least one meaningful pickup segment.

### Phase 2 — Public MVP and admin

- build visitor flow, admin auth/import/jobs/models/audit, SQLite operations, analytics/privacy controls, and deployment observability;
- add scheduled adapters only for approved sources.

**Exit:** acceptance scenarios, security review, accessibility checks, backup restore, and production smoke tests pass.

### Phase 3 — Coverage expansion

- add pickup makes/models only when their evidence gates pass;
- capture outcome/transaction feedback where lawful and consented;
- evaluate SUVs/sedans only after pickup accuracy, retention, and source economics are validated.

## 14. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Marketplace terms prohibit scraping | Product has no lawful data supply | Permission/licensed-feed gate; support imports and partner feeds; never bypass controls |
| Asking price differs from sale price | Estimate may overstate realizable value | Label as asking-price valuation; learn sale-price calibration only from consented outcomes |
| Sparse/biased Alberta data | Unfair or unstable estimates | Minimum segment counts, time holdout, slice metrics, intervals, refuse low-evidence predictions |
| Duplicate/stale listings | Artificially weights price observations | Identity resolution, price history, active/inactive lifecycle, recency weighting |
| Trim/cab/configuration missing | Confounded valuations | Normalize taxonomy; require or explicitly mark unknown; measure missingness |
| Market drift | Old model becomes inaccurate | Freshness/drift monitoring, scheduled retraining candidates, manual promotion/rollback |
| Visitor logging creates privacy exposure | Legal/trust harm | Data minimization, rotating identifiers, retention limits, consent/policy review |
| SQLite write contention | Jobs or UI block | WAL, short transactions, one bounded writer path, documented PostgreSQL trigger |

## 15. Open decisions requiring owner sign-off

1. Which source can provide written permission or a licensed Alberta feed?
2. Is the public output explicitly an asking-price estimate, or will transaction/outcome data be acquired?
3. Which pickup make/model is the first supported launch cohort after Ford Ranger feasibility testing?
4. What deployment host, backup destination, and admin identity/email mechanism will be used?
5. Will the product collect optional user feedback about an eventual sale price, and under what consent/privacy policy?

## 16. Go/no-go recommendation

**Conditional go.** Build Phase 0 and the offline proof now. Do not invest in production crawling or a polished public launch until a lawful, repeatable data supply is secured. The technical MVP is straightforward; data rights, representative coverage, and calibrated uncertainty are the critical product constraints.
