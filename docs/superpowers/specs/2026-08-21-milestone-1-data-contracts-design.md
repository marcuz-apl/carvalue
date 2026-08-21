# Milestone 1 — Data Rights and Contracts Design

**Status:** Draft for review  
**Date:** 2026-08-21  
**Scope:** Permission-safe source metadata, pickup taxonomy, normalized listing contract, and authorized fixtures

## Objective

Create the source-neutral contracts that let later ingestion and valuation work proceed without live marketplace access or ambiguous vehicle/listing data. M1 must make unauthorized automated collection fail closed and must preserve the units, provenance, and privacy constraints required by the PRD.

## In scope

1. A source permission record and preflight decision contract.
2. A deterministic Alberta pickup taxonomy with canonical values and aliases.
3. A normalized listing observation contract with explicit units and provenance.
4. Stable row-level rejection/quarantine reason codes and safe messages.
5. Sanitized, rights-documented fixtures based on the supplied Ford Ranger example.
6. Contract tests for valid rows, missing required fields, aliases, unit boundaries, permission blocks, and fixture field disappearance.

## Out of scope

- Network calls, marketplace adapters, browser automation, schedules, or credentials.
- Persistence migrations and production import commit semantics beyond contract-level tests; those are M2.
- CatBoost, model training, public API/UI, admin authentication, or deployment.
- Seller identity, contact details, free text, photos, VINs, or other unnecessary personal/source content.

## Proposed contracts

### Source permission record

Each source record has:

- stable source ID, name, source type, and origin/file description;
- permission status: `unknown`, `approved`, or `denied`;
- permission basis/owner notes;
- policy/robots review timestamp and optional expiry;
- permitted fields, retention deadline, attribution requirements, and rate limit;
- enabled state and adapter/parser version metadata.

Automated discovery/fetch is allowed only when status is `approved`, the review is current, the source is enabled, and required policy fields are present. `unknown`, `denied`, expired, or incomplete records return a stable blocked decision. Manual rights-confirmed fixtures may be used for development, but their provenance and rights metadata remain mandatory.

### Pickup taxonomy

Taxonomy values are canonical, lower-case domain values with normalized aliases. The first fixture cohort is Ford Ranger. The taxonomy may contain future pickup candidates, but a value is not exposed as supported until coverage and model gates pass.

The resolver must:

- normalize case, whitespace, punctuation, and accents deterministically;
- resolve make/model/trim within the correct parent;
- reject unknown make/model combinations rather than accepting arbitrary strings;
- preserve blank optional trim/configuration values as explicit missing data.

### Normalized listing observation

Required fields:

- source ID and source record ID;
- canonical make/model;
- model year as an integer;
- odometer as non-negative `mileage_km`;
- asking price as integer `price_cad_cents`;
- observed timestamp as UTC.

Optional valuation fields:

- canonical trim, drivetrain, seller type, cab style, box length, and Alberta region;
- permitted canonical URL/record reference;
- first/last seen timestamps, fetched timestamp, parser version, and content checksum.

The contract excludes seller names, phone numbers, email addresses, personal free text, photos, and unapproved raw content. Money never uses binary float; boundary conversions are explicit and tested.

### Rejection and quarantine

Normalization returns either a validated observation or a stable reason code with a safe message. Required failures include missing year/mileage/price, non-integer values, implausible ranges, non-Alberta location, ambiguous/non-CAD price, and unrecognized vehicle identity. Optional unknown values may be left blank only when the contract documents that behavior; they may not silently change vehicle identity.

## Data flow

```text
source metadata
    -> permission preflight (fail closed)
    -> sanitized fixture/file row
    -> header mapping and unit parsing
    -> taxonomy resolution
    -> required/optional validation
    -> normalized observation OR reason-coded rejection/quarantine
```

M1 ends at the normalized contract boundary. M2 owns database upsert, deduplication, price history, and import commit transactions.

## Error handling and observability

Public/safe messages expose only the stable reason and corrective meaning. Protected diagnostics may include parser details and row references but must not include credentials, cookies, or unnecessary personal/source content. Contract tests should count accepted, rejected, quarantined, and blocked rows without logging raw rows.

## Test strategy

- Unit tests for normalization, aliases, CAD/km conversion, bounds, timestamps, reason codes, and permission decisions.
- Fixture contract tests for the Ford Ranger workbook and a required-price-field disappearance.
- Negative tests proving unknown/denied/expired source records cannot authorize automated collection.
- Determinism tests proving the same sanitized input yields the same canonical observation and fingerprint inputs.
- No network dependency; tests run entirely from local authorized/synthetic fixtures.

## M1 acceptance criteria

1. Permission preflight fails closed for `unknown`, `denied`, disabled, and expired/incomplete sources.
2. A valid Ford Ranger fixture row normalizes to CAD cents, kilometres, canonical taxonomy values, UTC time, and complete provenance.
3. Arbitrary make/model strings cannot enter the normalized supported taxonomy.
4. Missing required price/year/mileage fields produce stable reason codes and cannot produce an observation.
5. Prohibited identity/contact/photo fields have no normalized contract fields.
6. The fixture contract test fails when the required price field disappears.
7. All M1 tests are deterministic and do not access a live provider.

## Open decisions deferred to later milestones

- Exact licensed provider/dealer-feed choice: M0/M1 owner decision, not encoded as an adapter now.
- Database schema/migrations and deduplication persistence: M2.
- First model-supported segment and launch metrics: M3.
- Public/admin authentication and deployment: M4–M7.
