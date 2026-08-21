# CarValue

CarValue is a planned web platform for estimating used pickup-truck asking prices in Alberta, Canada. It will combine permissioned market data, an explainable valuation model, a public valuation experience, and an authenticated administration area for data ingestion and model governance.

## Project status

CarValue is in the permission-safe foundation phase. The repository has a Python modular-monolith foundation, SQLite-oriented domain models, spreadsheet validation primitives, versioned Git hooks, and a passing baseline test suite. Production data collection remains disabled until a source has documented permission and reuse terms.

The immediate blocker is securing a lawful, repeatable source of Alberta vehicle-listing data. AutoTrader.ca and CarGurus.ca are not approved for automated collection, and MarketCheck requires further signup and licensing review before its data may be persisted or used for model training.

## MVP scope

- Used pickup trucks in Alberta
- Prices in CAD and mileage in kilometres
- Asking-price estimate with an 80% prediction interval
- Confidence, comparable count, data freshness, and clear disclaimers
- Public valuation flow with no visitor account required
- Admin tools for approved imports, scheduled ingestion, data quality, model evaluation, promotion, and rollback
- SQLite storage for the initial single-host deployment

## Valuation approach

The supplied Ford Ranger example uses a two-feature Statsmodels OLS regression based on year and mileage. CarValue will retain that model as a transparent benchmark and evaluate CatBoost as the first production candidate using chronological validation, segment-level error metrics, and calibrated uncertainty.

The current example workbook contains 32 deduplicated observations and is a baseline fixture—not a production training dataset.

## Planned architecture

- **Frontend and admin UI:** Next.js with TypeScript
- **API and domain services:** FastAPI, Pydantic, SQLAlchemy, and Alembic
- **Background jobs:** Python worker with APScheduler
- **Valuation:** Statsmodels baseline, CatBoost candidate, and scikit-learn-compatible evaluation tooling
- **Database:** SQLite with a documented PostgreSQL migration path
- **Approved browser automation:** Playwright with deterministic extraction and validation

## Data acquisition principles

Data acquisition is deny-by-default. A source must have documented permission, permitted fields, retention rules, attribution requirements, and rate limits before automation is enabled. CarValue will not bypass authentication, CAPTCHAs, robots directives, paywalls, bot controls, or other access restrictions.

The preferred long-term strategy combines licensed automotive data with direct Alberta dealer feeds and open-government enrichment.

## Repository guide

- [Product requirements](./PRD.md)
- [Engineering and agent guidance](./AGENTS.md)
- [Current project handoff](./HANDOFF.md)
- [Source acquisition strategy](./docs/SOURCE-ACQUISITION-STRATEGY.md)
- [MarketCheck onboarding and resume guide](./docs/MARKETCHECK-ONBOARDING-AND-RESUME.md)
- [Original initiative](./Initiative.md)
- [Ford Ranger valuation example](./Ford-Ranger/Valuation-of-a-used-Ford-Ranger.md)

## Delivery roadmap

CarValue is delivered through gated milestones. Each milestone must meet its exit criteria before dependent work begins. The detailed scope, dependencies, and no-go conditions live in [the technical roadmap](./docs/TECHNICAL-ROADMAP.md).

1. **Foundation hardening:** package boundaries, migrations, configuration, lint/type cleanup, and test infrastructure.
2. **Data rights and contracts:** source permission metadata, pickup taxonomy, normalized listing contract, and authorized fixtures. **Current milestone.**
3. **Import and data quality:** CSV/XLSX preview, validation, provenance, deduplication, price history, and safe SQLite upserts.
4. **Offline valuation proof:** OLS benchmark, CatBoost candidate, chronological evaluation, calibrated 80% intervals, refusal rules, and model card.
5. **Valuation API:** validated public requests and explainable asking-price results.
6. **Admin and workers:** authenticated operations, source/run management, leases, retries, audit, snapshots, model promotion, and rollback.
7. **Public web experience:** accessible responsive valuation flow, results, feedback, privacy controls, and error states.
8. **Launch hardening:** security, accessibility, backup/restore, observability, deployment, and production smoke tests.
9. **Coverage expansion:** additional makes, models, and vehicle classes only after evidence gates pass.

No live marketplace adapter, automated collection, or polished public launch is scheduled ahead of the applicable permission, data-volume, accuracy, and calibration gates.

## Important disclaimer

CarValue is intended to provide evidence-based asking-price estimates. It is not a certified appraisal, guaranteed sale price, trade-in offer, lending value, or insurance valuation.
