# MarketCheck Onboarding and Resume Guide

**Status:** Paused — MarketCheck account signup is not yet complete  
**Prepared:** August 9, 2026  
**Project:** CarValue Alberta Pickup Valuator  
**Next action:** Complete MarketCheck signup or contact MarketCheck support

## Purpose

This document records what CarValue can and cannot do with MarketCheck under its standard terms, the safe same-day evaluation process, the permissions required for the intended valuation model, and the exact steps for resuming work after account access is available.

Do not place an API key, client secret, access token, password, cookie, or other credential in this document, source control, an issue, or a chat message.

## Current state

- MarketCheck has been selected for an initial technical and Alberta-coverage evaluation.
- MarketCheck signup could not be completed yet.
- No MarketCheck API key has been configured.
- No live MarketCheck query has been run by CarValue.
- No MarketCheck data has been stored, imported into SQLite, or used for model training.
- The local Ford Ranger workbook currently contains 32 rows and zero exact duplicate rows.
- Development may continue against synthetic or rights-confirmed fixtures while signup and licensing are unresolved.

## Critical licensing finding

CarValue can begin a limited technical evaluation using MarketCheck, but the standard MarketCheck terms do **not** authorize MarketCheck to serve as the persistent training-data pipeline described in `PRD.md`.

The standard terms restrict:

- caching, indexing, or persisting substantial portions of MarketCheck data;
- systematically extracting inventory into an independent database;
- using MarketCheck data to train, fine-tune, or improve a generalized machine-learning or AI model;
- producing synthetic or derivative training datasets;
- building a product that competes with or approximates MarketCheck’s data products;
- using MarketCheck results to identify targets for an independent data-acquisition pipeline.

MarketCheck states that some commercial, high-volume, bulk, or production uses may require a separate written enterprise agreement. See the current [MarketCheck Terms of Service](https://www.marketcheck.com/terms_of_service/) before signup and again before any production use.

### Consequence for CarValue

Without a separate written agreement, CarValue must not:

1. schedule systematic Alberta inventory downloads;
2. retain MarketCheck listing history in SQLite;
3. train CatBoost, OLS, or another valuation model using MarketCheck records;
4. use MarketCheck to populate an independent comparable-listing database;
5. deploy a MarketCheck-derived commercial valuation model.

A free or paid API subscription alone must not be treated as permission for these activities.

## What can begin before enterprise permission

The following work can proceed without storing live MarketCheck data:

- define the source-neutral ingestion interfaces;
- implement MarketCheck request and response schemas from public documentation;
- create synthetic, sanitized API fixtures;
- implement configuration using environment variables;
- add request timeouts, bounded retries, rate-limit handling, and safe errors;
- implement unit and contract tests against fixtures;
- design a one-shot field-coverage report;
- document mileage/unit conversion and provenance requirements;
- prepare a live smoke test that does not persist the response;
- prepare the enterprise licensing request.

Only a very small number of transient API calls should be used for connection and field verification under the standard account. Do not turn the free tier into a systematic coverage sweep while licensing remains unresolved.

## Account setup when ready

MarketCheck currently requires an account and explicit subscription to an API package, including the free package.

1. Open the [MarketCheck Developer Portal](https://developers.marketcheck.com/).
2. Create or finish the account manually with accurate information.
3. Review and accept the current terms only if they are acceptable.
4. Subscribe explicitly to the free API package or trial.
5. Open the API Keys section.
6. Generate an API key and client secret.
7. Prefer an expiring or endpoint/IP-restricted development credential when the portal supports it.
8. Store the API key locally as `MARKETCHECK_API_KEY`.
9. Never paste the key into chat, documentation, test fixtures, or source code.

Refer to the official [MarketCheck authentication documentation](https://docs.marketcheck.com/docs/get-started/api/authentication).

### Local secret configuration

When the application skeleton exists, use an ignored local environment file:

```dotenv
MARKETCHECK_API_KEY=replace_with_local_secret
```

The repository should contain only a safe example:

```dotenv
MARKETCHECK_API_KEY=
```

Before using a `.env` file, confirm that `.env` and environment-specific variants are ignored by source control. Do not commit the populated file.

## Free-tier limits

MarketCheck currently documents the following free-package limits:

- 500 calls per calendar month;
- five calls per second;
- quota tracked at account level across API keys;
- unused quota does not roll over;
- requests beyond quota return HTTP 429;
- geographic and pagination restrictions may also apply to the package.

Check the current [quota and rate-limit documentation](https://docs.marketcheck.com/docs/get-started/api/quota-and-rate-limits) and [pricing page](https://www.marketcheck.com/apis/pricing/) because limits and prices may change.

## Initial Alberta smoke test

MarketCheck documents Canadian dealer inventory through the active inventory endpoint:

```text
GET https://api.marketcheck.com/v2/search/car/active
```

The first request should be narrowly limited to five Alberta Ford Ranger results:

```text
country=ca
state=AB
make=Ford
model=Ranger
car_type=used
rows=5
facets=trim
stats=price,miles
```

See the official [Inventory Search API documentation](https://docs.marketcheck.com/docs/api/cars/inventory/inventory-search).

### Smoke-test rules

- Read the API key from `MARKETCHECK_API_KEY`; never hardcode it.
- Do not log the request URL if it contains the API key as a query parameter.
- Do not save the raw response to disk or SQLite.
- Do not make paginated or repeated collection requests.
- Print only a field-coverage summary, counts, units, and safe example values.
- Redact listing URLs, VINs, dealer contacts, and credentials from diagnostics unless explicitly needed and permitted.
- Stop on HTTP 401, 403, or 429 rather than attempting to evade access controls.

### Items to verify from the response

- whether Alberta returns usable Ford Ranger records;
- actual field names and nesting;
- price currency and whether CAD is explicit;
- whether the mileage field is expressed in miles or kilometres for Canadian listings;
- trim, drivetrain, cab, and box-length coverage;
- source and dealer attribution requirements;
- first-seen, last-seen, and price-change fields;
- duplicate behavior;
- null and malformed-value rates.

The CarValue domain model must continue to store and display kilometres and CAD. Any source conversion must be explicit, deterministic, and tested.

## Written permission request

Send the following draft to `support@marketcheck.com`. This is a draft only; it has not been sent.

### Subject

```text
Data and ML licensing request — Alberta vehicle valuation platform
```

### Message

```text
Hello MarketCheck team,

We are developing CarValue, a vehicle valuation platform initially focused on
used pickup trucks in Alberta, Canada.

We would like to evaluate MarketCheck’s Canadian dealer inventory API and
potentially enter an enterprise agreement. Our intended use includes:

- querying Alberta used-vehicle inventory daily;
- retaining normalized listing observations and price history;
- training a proprietary valuation model using year, mileage, trim,
  drivetrain, seller type, and configuration;
- displaying derived price estimates, uncertainty ranges, aggregate
  statistics, and a limited number of comparable listings;
- not reselling or exposing the underlying bulk dataset.

Please confirm whether a written licence can authorize:

1. persistent storage and historical retention;
2. machine-learning model training;
3. commercial deployment of the resulting model;
4. continued use of trained model artifacts following contract termination;
5. display of aggregates and comparable listings;
6. Canadian coverage for Alberta and applicable attribution requirements.

Please also provide pricing, sample Alberta coverage, sandbox availability,
retention limits, and the relevant enterprise agreement.

Thank you.
```

## Questions requiring written answers

Do not proceed to live data ingestion or model training until the following are answered in the signed agreement or an authoritative written amendment:

1. May CarValue store individual Alberta listings?
2. What portion of the dataset may be stored, and for how long?
3. May CarValue preserve first-seen, last-seen, and price history?
4. May MarketCheck records be used to train CarValue’s CatBoost model?
5. Is CarValue considered a prohibited competing valuation product?
6. Who owns the trained model and derived statistics?
7. May the trained model remain in use after the agreement ends?
8. May CarValue display a point estimate, prediction interval, and aggregate comparables?
9. May individual comparable listings be shown, and what attribution is required?
10. Does Canadian coverage include Alberta dealer inventory for the target pickup models?
11. Are Canadian mileage values supplied in kilometres or miles?
12. Are inactive/recent listings confirmed sales, expired listings, or an indistinguishable mixture?
13. Which endpoints and fields are included in the proposed package?
14. What are the setup, subscription, data, usage, and overage costs?
15. What deletion, audit, security, and termination obligations apply?

## Decision gates

### Gate A — Technical access

Pass when:

- signup succeeds;
- a free or trial subscription is active;
- a development credential is stored securely;
- one narrow, non-persistent Alberta smoke test succeeds.

### Gate B — Data fitness

Pass when the smoke test or provider-supplied sample demonstrates acceptable Alberta coverage and field quality for price, mileage, year, make, model, trim, and required configuration fields.

### Gate C — Legal and commercial rights

Pass only when written terms authorize the intended persistence, historical dataset, model training, commercial output, attribution, and post-termination behavior.

### Gate D — Production ingestion

Pass after Gates A–C, source configuration is marked approved, contract fixtures pass, and retention/rate limits are encoded in configuration.

No scheduled MarketCheck collection or model training may begin before Gate C passes.

## Resume checklist

When work resumes, begin here:

1. Re-read this document, `PRD.md`, `AGENTS.md`, and `docs/SOURCE-ACQUISITION-STRATEGY.md`.
2. Confirm whether signup was completed.
3. Confirm whether a populated local secret exists without printing its value.
4. Confirm the current MarketCheck terms and pricing have not changed.
5. Check for a reply from MarketCheck and save the approved rights as non-secret source-policy metadata.
6. If only technical access is available, build or run the non-persistent smoke test.
7. If written ML/persistence permission is absent, continue with mock fixtures only.
8. If written permission is granted, review its limits before enabling persistence.
9. Implement source configuration with `permission_status=approved`, review/expiry dates, permitted fields, retention, rate limits, and attribution.
10. Run a small Alberta coverage assessment before any full data acquisition.

## Alternatives if signup or permission fails

If MarketCheck signup remains unavailable, coverage is insufficient, pricing is unsuitable, or the required rights are denied:

1. request Canadian Black Book Retail API and valuation API proposals;
2. request a CARFAX Canada Vehicle Valuation API proposal;
3. begin the Alberta dealer-feed partnership program;
4. continue with rights-confirmed CSV/XLSX imports and open government enrichment;
5. keep MarketCheck disabled rather than attempting account, quota, or policy workarounds.

## Related project documents

- [`PRD.md`](../PRD.md)
- [`AGENTS.md`](../AGENTS.md)
- [`SOURCE-ACQUISITION-STRATEGY.md`](./SOURCE-ACQUISITION-STRATEGY.md)
- [`Initiative.md`](../Initiative.md)

