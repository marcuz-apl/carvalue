# ADR 0002: Coverage Expansion Governance & Segment Regression Gates

**Status:** Accepted  
**Date:** August 2026  
**Context:** PRD Section 12 & Technical Roadmap Milestone M8  

---

## Context and Problem Statement

CarValue's initial MVP was focused strictly on mid-size and half-ton Alberta pickup trucks (e.g. Ford Ranger, F-150, Silverado 1500). To expand coverage into Heavy-Duty pickup trucks (3/4-ton and 1-ton: F-250/F-350, Silverado 2500HD/3500HD, Sierra 2500HD/3500HD, Ram 2500/3500) and Alberta regional sub-markets without compromising estimation reliability or violating data acquisition rules, explicit expansion criteria and validation gates are required.

---

## Decision Drivers

1. **Deny-by-Default Data Rights:** No automated source may be ingested without verified permission and unexpired policy review.
2. **Segment Accuracy & Calibration:** Expanding training data across heavy-duty commercial fleets must not degrade prediction accuracy on consumer half-ton/mid-size trucks.
3. **Refusal Over Fabrication:** Sparse configurations ($<4$ comparables) or unobserved sub-regions must trigger explainable refusal rather than interpolated guesses.
4. **Zero Personal Identifiers:** Regional segmentation must not track precise GPS or postal code coordinates of visitors.

---

## Expansion Policy & Governance Gates

### 1. New Segment Ingestion Gate
Before any new pickup truck family or trim is onboarded:
- Ingestion source must satisfy `SourcePolicy.permission_status == 'approved'`.
- Normalized taxonomy aliases must be registered in `carvalue_core.taxonomy.seed_pickup_taxonomy()`.
- Sample threshold requirement: A minimum of 50 historical observations across the model family must exist in the local dataset before candidate model fitting.

### 2. Segment Regression Gate (`SegmentRegressionGate`)
When benchmarking a candidate model against the active model:
- **Global Gate:** Overall test-set MAE must equal or improve baseline MAE.
- **Slice Gate:** For every individual supported segment with $\ge 5$ test samples, slice MAE degradation must not exceed **8.0%**.
- **Rule:** A candidate model that achieves a 10% global MAE improvement but suffers a 9% MAE degradation on `ford:ranger` is **automatically blocked from promotion**.

### 3. Regional Sub-Market Segmentation
- Supported Alberta regions: `calgary_region`, `edmonton_region`, `red_deer_central`, `lethbridge_south`, `medicine_hat_southeast`, `fort_mcmurray_north`, `grande_prairie_peace`, and `rural_alberta`.
- Regional variations are treated as discrete categorical features in CatBoost models. If regional comparables are insufficient, the valuation defaults to Alberta-wide pricing with clear metadata.

### 4. Visitor Feedback Loop
- User feedback (useful 👍 / not useful 👎) is captured anonymously via `POST /v1/valuations/feedback` and logged to `ValuationEvent.feedback_useful`.
- High negative feedback density ($>30\%$ not-useful on a segment) automatically flags that segment for manual quality review in `DataQualityIssue`.

---

## Consequences

- **Positive:** Ensures sustainable, defensible growth into high-value Alberta heavy-duty pickup segments while protecting existing baseline accuracy.
- **Positive:** Guarantees auditability and compliance with repository guardrails.
- **Negative / Trade-off:** Candidate models may require more iterations and hyperparameter tuning to satisfy both global and per-slice accuracy gates.
