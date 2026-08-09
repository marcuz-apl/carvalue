# Alberta Vehicle Data Source Acquisition Strategy

**Status:** Recommended approach  
**Prepared:** August 9, 2026  
**Scope:** Alberta used pickup valuation data

## Executive recommendation

The best alternative to crawling AutoTrader.ca and CarGurus.ca is a hybrid acquisition strategy:

1. Use a licensed automotive API to launch and validate demand.
2. Build a proprietary Alberta dataset through direct dealer feeds.
3. Add open government data for vehicle specifications and regional context.
4. Gradually collect consented transaction outcomes to improve from asking-price estimates toward true sale-value estimates.

There is unlikely to be a broad, free, production-grade Canadian used-vehicle price dataset. The practical trade-off is money versus time: licensed APIs provide fast coverage, while dealer partnerships cost less financially and create a more defensible dataset but take longer to establish.

## Candidate sources

| Source | Data available | Cost/access | Best use |
|---|---|---:|---|
| Canadian Black Book | Canadian valuations, trim-level retail listings, and market statistics | Commercial; contact provider | Strongest Canada-specific licensed option |
| MarketCheck | Active and recent Canadian dealer inventory | Free prototype tier; paid production | Fastest feasibility dataset |
| CARFAX Canada | Province-aware market valuation and VIN/history-adjusted valuation | Commercial | Benchmark or valuation-provider integration |
| Alberta dealer feeds | Inventory, price changes, mileage, and potentially transaction prices | Partnership effort | Best long-term proprietary source |
| Canadian and Alberta open data | Specifications, registrations, and geographic context | Free/open licence | Enrichment only—not prices |
| Consumer submissions | Private-sale asking and transaction outcomes | Product acquisition cost | Later private-sale calibration |

## 1. MarketCheck for an immediate proof of concept

MarketCheck documents active and recent dealer-inventory APIs covering Canada. Available fields and capabilities include price, mileage, trim, geography, pagination, facets, and market statistics.

Its published free tier currently provides:

- 500 API calls per month;
- five calls per second;
- a 100-mile search-radius restriction;
- a 500-row pagination limit.

Published paid plans start at USD 299 per month plus usage fees. Refer to the [MarketCheck Canadian inventory documentation](https://docs.marketcheck.com/docs/api/cars/inventory/introduction) and [current API pricing](https://www.marketcheck.com/apis/pricing/) before making a purchasing decision.

The free tier should be sufficient to test:

- Ford Ranger listing coverage around Calgary and Edmonton;
- listing quality and trim normalization;
- the proposed CatBoost valuation model;
- time-based price-history collection;
- whether Alberta coverage can meet the minimum sample thresholds in the PRD.

### Rights to confirm before using MarketCheck data

Obtain written confirmation that the proposed licence permits:

- storing individual listings;
- retaining historical observations;
- training a derivative valuation model;
- displaying aggregates and comparable listings;
- continuing to use a trained model after the subscription ends;
- identifying or attributing the underlying listing source where required.

An API subscription must not be assumed to include machine-learning, indefinite-retention, or derivative-model rights.

## 2. Canadian Black Book for a production licence

Canadian Black Book is likely the strongest Canada-specific commercial fit. Its product information describes Retail Listings data normalized to Black Book vehicle descriptions at trim level, with broad Canadian dealership and listing coverage.

The [Canadian Black Book API offering](https://www.canadianblackbook.com/api/) includes used-car and retail products. Its [developer portal](https://developer.canadianblackbook.com/) provides Used Car, New Car, and Retail APIs, including GraphQL documentation and a test harness.

Request two separate proposals:

1. Alberta raw or aggregated retail-listing access;
2. direct vehicle-valuation API access.

If raw listing access is affordable and includes model-training rights, it could supply the CatBoost training dataset. If only valuation outputs are licensed, use the API as the initial valuation engine or as an external benchmark. Do not use its output as synthetic training labels unless the licence explicitly permits that use.

## 3. CARFAX Canada as a benchmark or premium option

CARFAX Canada offers a Vehicle Valuation API. Its market-based value considers:

- year, make, model, and trim;
- odometer reading;
- province;
- seasonality;
- daily market data.

Its VIN-specific history-based value can additionally account for accident and damage history, service history, ownership history, vehicle use, and postal code. See the [CARFAX Canada automotive data solutions](https://go.carfax.ca/aro-solutions).

Potential uses include:

- validating CarValue predictions against an established Canadian provider;
- offering premium VIN-specific valuations later;
- covering sparse vehicles for which CarValue has insufficient evidence;
- using CARFAX as the initial valuation provider while the proprietary dataset grows.

This approach does not automatically provide the underlying listings required to train an independent model.

## 4. Alberta dealer partnerships

Direct dealer feeds are the recommended long-term strategy. CarValue should establish a **CarValue Dealer Data Program** and recruit an initial group of independent Alberta pickup dealers.

### Value offered to participating dealers

Possible incentives include:

- a nightly market-position dashboard;
- stale-inventory alerts;
- price-change recommendations;
- a free valuation widget for the dealer’s website;
- aggregate Alberta pickup trends;
- early access to CarValue’s admin and analytics features.

### Feed delivery

Accept a nightly CSV, JSON, API, or SFTP feed. The automotive industry already uses structured vehicle inventory feeds. Google’s published [vehicle-listing feed specification](https://developers.google.com/vehicle-listings/integration-process/feed-setup) provides a useful starting schema, even when the feed is delivered directly to CarValue rather than Google.

The minimum partner feed should contain:

```text
dealer_id
inventory_id
vin
year
make
model
trim
mileage_km
drivetrain
cab_style
box_length
condition
asking_price_cad
first_listed_at
updated_at
removed_at
final_asking_price_cad   # optional
transaction_price_cad    # optional but extremely valuable
sold_at                  # optional
```

Do not collect buyer identity, financing details, contact information, or bill-of-sale documents.

### Data-sharing agreement

The dealer agreement should explicitly define:

- permission to store and normalize contributed data;
- permission to use the data for model training;
- ownership and permitted use of derivative models;
- whether individual listings or only aggregates may be displayed;
- retention rights after the partnership ends;
- confidentiality requirements for transaction prices;
- deletion requirements;
- source attribution;
- security, incident, and breach obligations.

The [AMVIC portal](https://www.amvic.org/salesperson/) can help identify licensed Alberta automotive businesses for partnership outreach.

### Initial recruitment target

Recruit five pilot dealers before attempting broad coverage. Prefer a geographical mixture such as:

- Calgary;
- Edmonton;
- Red Deer;
- Lethbridge or Medicine Hat;
- one rural Alberta market.

After confirming feed reliability and dealer value, expand toward 10–20 participating dealers.

## 5. Government and open data

Open government datasets are valuable for enrichment but do not provide the asking-price or transaction-price target required by the valuation model.

Transport Canada publishes [Canadian Vehicle Specifications](https://open.canada.ca/data/en/dataset/913f8940-036a-45f2-a5f2-19bde76c1252) by model year. These records can help normalize vehicle dimensions, configurations, and specifications.

Alberta publishes [vehicle-registration statistics](https://regionaldashboard.alberta.ca/region/standard/vehicle-registrations/) that can help measure regional demand and prioritize coverage.

Use these datasets for:

- vehicle taxonomy and specification enrichment;
- regional weighting;
- coverage planning;
- demand and seasonality context.

Do not treat them as price observations or transaction outcomes.

## 6. Consumer-contributed outcomes

Once the public product is operating, visitors may optionally contribute a vehicle’s eventual sale outcome. This can improve private-sale calibration and address the difference between advertised and realized prices.

Potential fields include:

- valuation request ID;
- final asking price;
- transaction price;
- sale date;
- general seller type;
- material condition change since valuation.

Participation must be optional and covered by an appropriate privacy notice. Do not collect buyer identity or retain uploaded bills of sale. Apply outlier and fraud checks before using contributed outcomes for training.

## Approaches to avoid

### Third-party marketplace scraping services

A provider that scrapes AutoTrader.ca or CarGurus.ca on CarValue’s behalf does not necessarily solve the underlying rights problem. Outsourcing the crawler mechanics does not automatically grant permission to store, display, reuse, or train models on the data.

### Access-control evasion

Do not use CAPTCHA solving, proxy rotation, stealth browser automation, fingerprint spoofing, account automation, or other methods intended to bypass technical or policy restrictions.

### Unverified public datasets

Do not rely on scraped Kaggle or community datasets in production when provenance, consent, freshness, or reuse rights are unclear. They may be useful for temporary software-development fixtures only if their licence permits it.

### Synthetic labels from another valuation API

Do not train the CarValue model on predictions returned by another valuation provider unless the contract explicitly permits it. This would reproduce the provider’s biases, provide no transaction ground truth, and may amount to prohibited model extraction.

### Listing disappearance as a sale signal

A removed listing may have sold, expired, moved to another platform, or been withdrawn. Treat removal as `inactive`, not as a confirmed sale, and never infer a transaction price without supporting evidence.

## Recommended rollout

### Stage 1 — Coverage feasibility

1. Contact MarketCheck and obtain written confirmation of storage, retention, display, and model-training rights.
2. Use its free tier, if permitted, to measure Alberta Ford Ranger coverage around Calgary and Edmonton.
3. Request Canadian Black Book Retail API and valuation API proposals.
4. Request a CARFAX Canada Vehicle Valuation API proposal.
5. Compare field coverage, Alberta sample size, freshness, rights, and total cost.

### Stage 2 — Source-neutral ingestion

1. Implement the source-neutral feed contract described above.
2. Support CSV/XLSX import first, followed by JSON/API and SFTP ingestion.
3. Preserve source provenance, listing history, data rights, and retention metadata.
4. Keep marketplace/provider adapters separate from the normalized valuation dataset.

### Stage 3 — Dealer pilot

1. Recruit five Alberta dealer partners.
2. Import complete inventory snapshots nightly.
3. Record price changes and inactive listings.
4. Ask partners for optional de-identified transaction price and sold-date fields.
5. Return useful inventory analytics to participating dealers.

### Stage 4 — Initial model

1. Train the first model only on data whose licence permits machine learning.
2. Use a chronological holdout and the model acceptance criteria in `PRD.md`.
3. Compare results with Canadian Black Book or CARFAX values where the licence permits benchmarking.
4. Label the initial output as an asking-price estimate.

### Stage 5 — Sale-price calibration

1. Accumulate dealer-confirmed and consented consumer transaction outcomes.
2. Measure the asking-to-transaction-price difference by seller type and segment.
3. Introduce a separate calibrated sale-price output only when sample size and accuracy are sufficient.

## Provider evaluation checklist

Before selecting any provider, record answers to the following:

- Does Canadian coverage include Alberta and the required pickup models?
- Are dealer and private listings both available?
- Are price, mileage, trim, drivetrain, cab, box length, location, and timestamps available?
- Are historical price changes available?
- What does an inactive or recent listing mean?
- May CarValue retain individual records and for how long?
- May the records be used to train a valuation model?
- Who owns the trained model and derived aggregates?
- Can the trained model remain in use after contract termination?
- May CarValue show comparable listings or only aggregates?
- What attribution is required?
- What rate limits, pagination limits, and geographic restrictions apply?
- What are the setup, subscription, usage, and overage fees?
- Is a sandbox, trial, or sample Alberta extract available?
- What happens if an upstream source withdraws permission?

## Final recommendation

Use MarketCheck for a rights-confirmed feasibility experiment, while evaluating Canadian Black Book and CARFAX Canada as licensed production providers. In parallel, make Alberta dealer feeds the strategic data asset.

If the budget is strictly zero, begin with dealer partnerships, rights-confirmed spreadsheet/feed uploads, and open-data enrichment. This route will be slower, but it can produce a lawful and defensible proprietary dataset instead of creating permanent dependence on a marketplace or data vendor.

