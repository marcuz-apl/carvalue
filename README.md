# CarValue

CarValue is a planned web platform for estimating used pickup-truck asking prices in Alberta, Canada. It will combine permissioned market data, an explainable valuation model, a public valuation experience, and an authenticated administration area for data ingestion and model governance.

## Project status

CarValue is currently in the product-definition and data-source feasibility phase. The application has not yet been scaffolded.

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

## Next steps

1. Resolve MarketCheck signup and licensing, or select another approved acquisition route.
2. Confirm whether application scaffolding should begin while data licensing is pending.
3. Define the normalized vehicle-listing schema and source permission model.
4. Build permission-safe ingestion interfaces and synthetic contract fixtures.
5. Establish the OLS baseline and CatBoost evaluation pipeline once rights-confirmed data is available.

## Important disclaimer

CarValue is intended to provide evidence-based asking-price estimates. It is not a certified appraisal, guaranteed sale price, trade-in offer, lending value, or insurance valuation.

