# AGENTS.md — CarValue Engineering Guide

These instructions apply to the entire repository. They supplement the higher-level Codex/ECC instructions supplied by the workspace.

## Mission and source of truth

Build an explainable used-pickup asking-price valuator for Alberta, Canada. The product contract is `PRD.md`; the small Ford Ranger spreadsheet and regression notes are baseline examples, not production truth.

If code and `PRD.md` disagree, stop and surface the conflict before changing product behavior. Keep the MVP limited to Alberta pickup trucks unless the user explicitly expands scope.

## Mandatory product guardrails

- Always use CAD and kilometres at system boundaries and in the UI. Make conversions explicit and tested.
- Say “asking-price estimate,” not appraisal, guaranteed sale price, trade-in offer, or confirmed market value.
- Every valuation must include an uncertainty range, evidence/confidence label, valuation date, data freshness, comparable count, and disclaimer.
- Prefer “Insufficient Data” to fabricated precision for unsupported, sparse, stale, or out-of-distribution inputs.
- Do not implement a fixed dealer-to-private discount unless representative data validates and monitors it.
- Do not collect public-user identity merely to provide a valuation.

## Data acquisition: deny by default

Network tools are read-only by default under the workspace policy. In addition:

- Never run, implement, schedule, or enable an automated source unless its `sources` record is explicitly approved and documents permission/licence, terms and robots review, review date, allowed fields, retention, attribution, and rate limits.
- AutoTrader.ca and CarGurus are **not approved sources by default**. Their public availability is not permission. Require written/licensed access or a documented legal approval before automation.
- Never bypass a login, CAPTCHA, paywall, bot control, robots directive, rate limit, or access restriction. Do not add stealth plugins, proxy rotation, CAPTCHA solving, fingerprint spoofing, or credential automation.
- Do not collect seller names, phone numbers, email addresses, personal free text, or photos. Store only valuation-relevant vehicle/listing facts allowed by the source.
- Prefer licensed feeds, permitted dealer feeds, properly licensed open datasets, and rights-confirmed CSV/XLSX imports.
- A source policy change must fail closed: disable collection until reviewed.
- External mutations—publishing, deployment, pushing, source/account changes, paid services, or remote job dispatch—require explicit user approval.

## Intended architecture

Until an accepted architecture change is recorded, use a modular monolith:

- `apps/web`: Next.js + TypeScript public UI and admin UI;
- `services/api`: FastAPI, Pydantic, SQLAlchemy, and Alembic;
- `services/worker`: permission-gated ingestion, scheduling, data quality, and training jobs;
- `packages/schemas` or equivalent: versioned contracts shared at boundaries;
- `tests/fixtures`: saved, authorized, sanitized source fixtures;
- `data/`: local development data only, ignored by Git except tiny documented fixtures;
- `models/`: generated artifacts ignored by Git except deliberately versioned test fixtures;
- `docs/adr`: architectural decisions that materially change PRD assumptions.

Do not introduce microservices, a queue broker, Kubernetes, a cloud database, or an LLM extraction dependency without evidence the modular monolith cannot satisfy the requirement.

## Domain and storage conventions

- Money is integer cents in storage and typed decimal/integer values in application logic; never binary float for persisted currency.
- Odometer is a non-negative integer in kilometres. Name fields with units where ambiguity is possible, e.g. `mileage_km`, `price_cad_cents`.
- Store timestamps in UTC; localize for display. Schedules must record their IANA time zone (`America/Edmonton` for Alberta), including DST behavior.
- Enable SQLite foreign keys and WAL mode, configure a busy timeout, keep write transactions short, and use migrations for every schema change.
- Preserve provenance: source, source record ID/canonical URL where permitted, first/last seen, fetched time, parser version, and content checksum.
- Upsert observations and append price history; do not overwrite history or duplicate a listing.
- Raw source content has an explicit retention deadline and must never include unnecessary personal data.
- Secrets come from environment/secret storage. Never commit secrets, cookies, credentials, production databases, raw crawls, or model artifacts containing restricted data.

## Ingestion adapter contract

Every source adapter must expose the equivalent of discover/fetch/parse/normalize operations and include:

1. permission metadata and fail-closed preflight;
2. bounded concurrency, source-specific rate limiting, timeout, and identifiable user agent where permitted;
3. deterministic structured extraction—no LLM required for correctness;
4. schema validation and explicit reject/quarantine reason codes;
5. idempotent upsert semantics and conservative deduplication;
6. retry with capped exponential backoff/jitter and no retry for permanent 4xx/policy failures;
7. saved authorized fixtures and parser contract tests;
8. run counters for fetched, accepted, updated, duplicate, quarantined, rejected, and failed;
9. structured errors that never leak source credentials or personal data.

Playwright is the default browser adapter for approved dynamic sources. Use direct HTTP parsing for approved sources when it is simpler and permitted. Crawl4AI may assist exploration of an approved source but cannot replace deterministic normalization, validation, or the permission gate. Firecrawl or any hosted service requires explicit approval if it transmits source data or incurs cost.

## Valuation and ML rules

- Keep the supplied two-feature Statsmodels OLS as a reproducible baseline only. Centre age to the valuation date; do not expose meaningless raw-year intercepts as product insight.
- Use CatBoost as the first nonlinear candidate and benchmark it against the simple baseline. Complexity must earn its place on untouched time-based data.
- Initial features: vehicle age, mileage kilometres, trim, drivetrain, and seller type. Add cab style, box length, region, listing age, or other features only after defining coverage, semantics, and missing-value behavior.
- Split chronologically by observation/listing date. Hyperparameter tuning must not see the final holdout.
- Report MAE in CAD, MdAPE, RMSE, sample count, and prediction-interval coverage/width. R² alone is never an acceptance gate.
- Produce an 80% interval using quantile regression or calibrated conformal prediction and validate empirical coverage.
- Evaluate slices by make/model, year/age, price band, seller type, region, and relevant configuration. A global improvement cannot hide a material supported-segment regression.
- Record dataset snapshot/version, code revision, feature schema, configuration, metrics, timestamp, and artifact hash for every trained model.
- Model promotion is explicit, authenticated, reversible, and audited. Training completion must not automatically activate a model.
- Add and test out-of-distribution, low-sample, stale-model, and excessive-interval-width refusal rules.
- Use asking prices as the target only when the UI clearly labels the result. Never describe listing disappearance as a confirmed sale or infer sale price without evidence.

## Security and privacy

- Validate inputs at every boundary with allowlists/ranges and parameterized database access.
- Protect admin sessions with strong password hashing, secure/HttpOnly/SameSite cookies, CSRF defense, session expiry, and rate limiting.
- Do not log passwords, tokens, cookies, complete raw request bodies, or raw IP addresses in product analytics.
- Use a rotating pseudonymous visitor identifier only when justified; do not fingerprint visitors.
- Separate security logs, product analytics, audit events, and source-run logs. Apply configured retention and deletion.
- Record all admin mutations in an append-only audit trail.
- Before launch, require a documented privacy review for Alberta/Canadian obligations and a threat model for admin/data ingestion.

## Coding standards

- Prefer small typed modules and explicit domain names over generic dictionaries/objects.
- Keep source-specific selectors and mapping logic inside its adapter; do not leak them into domain/model code.
- Keep UI, API, domain, persistence, ingestion, and ML boundaries separable and testable.
- Validate untrusted spreadsheet cells as data; never evaluate formulas or execute content.
- Return stable error codes plus safe user messages; retain detailed structured diagnostics only in protected logs.
- Update documentation and migrations in the same change as behavior/schema changes.
- Avoid unrelated refactors. Preserve user changes and inspect the working diff before handoff.

## Required development workflow

For features, bugs, and refactors, follow the repository/ECC TDD and verification skills when available:

1. Read `PRD.md` and the affected code/tests.
2. State the acceptance behavior and risks.
3. Write or update a failing test first where practical.
4. Make the smallest implementation that passes.
5. Refactor without changing behavior.
6. Run focused tests, then the relevant full suite.
7. Run formatter, linter, type checker, migration checks, and dependency/security audit appropriate to the changed stack.
8. Review `git diff` for secrets, generated/raw data, accidental scope changes, and missing docs.

Do not weaken, skip, or delete a test merely to obtain a green run. If a required check cannot run, report exactly why and what remains unverified.

## Minimum test expectations

- **Unit:** normalization, aliases, currency/units, validators, fingerprints, confidence/refusal rules, interval formatting.
- **Integration:** migrations, SQLite constraints/upserts/WAL behavior, import preview/commit, jobs/leases/retries, model registry/promotion/rollback, admin authorization/audit.
- **Adapter contract:** authorized fixtures, required-field disappearance, layout variants, throttling/policy stop, idempotent rerun.
- **ML:** leakage checks, chronological split, reproducibility, metric calculation, interval calibration, segment regression gates, unseen categories and out-of-domain behavior.
- **E2E:** visitor happy path, invalid/unsupported vehicle, insufficient data, admin login, import/rejection report, blocked unapproved source, job inspection, model promotion/rollback.
- **Accessibility/security:** keyboard flow, automated accessibility scan, input abuse, CSRF/session/authorization, dependency audit.

Aim for at least 80% coverage on changed business logic, but prioritize meaningful behavioral coverage over a percentage target.

## Definition of done

A change is done only when:

- PRD acceptance behavior is satisfied and tested;
- no source-policy, privacy, or product guardrail is weakened;
- relevant tests, lint, formatting, types, migrations, and security checks pass;
- model/data behavior includes provenance and reproducibility where applicable;
- admin mutations and failure paths are observable/audited;
- docs and example configuration are current;
- the final handoff lists changed files, verification performed, and any residual risk.

