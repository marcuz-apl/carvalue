# CarValue Project Handoff

**Handoff date:** August 9, 2026  
**Status:** Product definition complete; data acquisition paused at MarketCheck signup/licensing  
**Next thread:** Read this file first

## Objective

Build an Alberta-focused used-pickup asking-price valuator with a public valuation flow and an authenticated admin area for permissioned data ingestion, scheduling, quality review, and model governance.

## Current state

- Product and engineering requirements are documented; application code has not been scaffolded.
- The Ford Ranger workbook contains 32 rows, zero exact duplicates, and the columns `Year`, `Mileage`, and `Price`.
- No external listing data has been acquired, persisted, or used for training.
- MarketCheck signup has not been completed, and no API credentials are stored in the repository.
- Git is initialized on `master` and connected to `https://github.com/marcuz-apl/carvalue.git`.
- The ECC memory runtime is unavailable; this file is the authoritative handoff.

## Finalized decisions

- MVP scope: used pickup trucks in Alberta, with CAD prices and kilometre-based mileage.
- Output: asking-price estimate, 80% prediction interval, confidence/evidence label, comparable count, freshness, valuation date, and disclaimer.
- Unsupported, sparse, stale, or out-of-distribution requests return low confidence or `Insufficient Data`.
- Keep the supplied Statsmodels OLS model as a benchmark; evaluate CatBoost as the production candidate using chronological validation.
- Initial model features: vehicle age, mileage, trim, drivetrain, and seller type. Add cab/box/location fields only when data quality supports them.
- Do not apply a fixed dealer-to-private discount or treat removed listings as confirmed sales.
- Intended architecture: Next.js/TypeScript UI, FastAPI/Python API and ML, a Python scheduler/worker, and SQLite for the MVP.
- Data acquisition is deny-by-default. Do not crawl AutoTrader.ca or CarGurus.ca without written/licensed authorization, and never bypass access controls.
- The long-term acquisition strategy is licensed data plus direct Alberta dealer feeds and open-data enrichment.

## MarketCheck blocker

MarketCheck can technically query Canadian dealer inventory, but its standard terms restrict persistent dataset creation, systematic extraction, model training, and competing data products. CarValue must not store MarketCheck listings in SQLite, schedule repeated acquisition, or train a valuation model from them without a separate written agreement granting those rights.

The project owner could not complete MarketCheck signup. No live API request has been made.

Use the detailed [MarketCheck onboarding and resume guide](./docs/MARKETCHECK-ONBOARDING-AND-RESUME.md) for signup, licensing questions, the permission-request draft, smoke-test rules, and decision gates.

## Canonical documents

- [PRD](./PRD.md) — product scope, architecture, functional requirements, metrics, acceptance scenarios, and delivery phases.
- [Engineering guide](./AGENTS.md) — mandatory repository, security, privacy, ingestion, ML, and testing rules.
- [Source acquisition strategy](./docs/SOURCE-ACQUISITION-STRATEGY.md) — provider options, dealer partnerships, open-data enrichment, and fallback strategy.
- [MarketCheck runbook](./docs/MARKETCHECK-ONBOARDING-AND-RESUME.md) — detailed MarketCheck procedures and restrictions.
- [Original initiative](./Initiative.md) and [Ford Ranger example](./Ford-Ranger/Valuation-of-a-used-Ford-Ranger.md).

## Next-thread steps

1. Read this file, `PRD.md`, and `AGENTS.md`.
2. Ask whether MarketCheck signup succeeded or MarketCheck support replied.
3. Re-check MarketCheck’s current terms, limits, pricing, and Canadian coverage because they can change.
4. Choose one branch:
   - **No account:** diagnose the signup issue or contact MarketCheck; consider Canadian Black Book, CARFAX Canada, or dealer feeds in parallel.
   - **Account but no written ML/storage rights:** run only a narrow, non-persistent smoke test and develop against synthetic fixtures.
   - **Written enterprise rights granted:** review and encode the exact field, retention, training, display, attribution, and termination constraints before ingestion.
   - **MarketCheck rejected:** select the next licensed provider or begin the Alberta dealer-feed pilot.
5. If the owner wants engineering to start while licensing is pending, scaffold only the permission-safe modular-monolith foundation, source interfaces, synthetic fixtures, and tests. Do not enable scheduled collection.

## Open owner decisions

- Continue pursuing MarketCheck or prioritize another acquisition route.
- Begin application scaffolding before securing a production data licence.
- Select hosting, backup storage, and admin identity mechanisms.

## Successful next-thread outcome

Finish with one concrete result: MarketCheck technical access tested without persistence; written rights reviewed; MarketCheck rejected and a replacement selected; or permission-safe scaffolding implemented using synthetic fixtures. Report whether any live provider data was accessed or stored.
