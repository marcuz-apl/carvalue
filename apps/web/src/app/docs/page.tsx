"use client";

import Link from "next/link";
import React, { useEffect, useState } from "react";

interface TabCodeBlockProps {
  tabs: { label: string; code: string; language: string }[];
}

function CodeBlock({ tabs }: TabCodeBlockProps) {
  const [activeTab, setActiveTab] = useState(0);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(tabs[activeTab].code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="docs-code-frame">
      <div className="docs-code-header">
        <div className="docs-tabs-list">
          {tabs.map((tab, idx) => (
            <button
              key={tab.label}
              type="button"
              className={`docs-tab-btn ${activeTab === idx ? "active" : ""}`}
              onClick={() => setActiveTab(idx)}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <button type="button" className="docs-copy-btn" onClick={handleCopy}>
          {copied ? (
            <>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2.5">
                <polyline points="20 6 9 17 4 12" />
              </svg>
              <span style={{ color: "#10b981" }}>Copied!</span>
            </>
          ) : (
            <>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <pre className="docs-code-body">
        <code>{tabs[activeTab].code}</code>
      </pre>
    </div>
  );
}

const navSections = [
  {
    group: "Overview",
    items: [
      { id: "intro", label: "Introduction & Scope" },
      { id: "architecture", label: "Unified Port 4020 Architecture" },
    ],
  },
  {
    group: "Valuation Engine",
    items: [
      { id: "price-aging", label: "Observation-Anchored Age" },
      { id: "macro-drift", label: "Macro Price Drift Economics" },
      { id: "statistical-models", label: "OLS Baseline & CatBoost ML" },
      { id: "prediction-intervals", label: "80% Prediction Intervals" },
      { id: "refusal-rules", label: "Refusal & Evidence Rules" },
    ],
  },
  {
    group: "Taxonomy & Coverage (M9)",
    items: [
      { id: "categories", label: "All Alberta Vehicle Categories" },
      { id: "alberta-regions", label: "Regional Sub-Market Segments" },
    ],
  },
  {
    group: "API Reference",
    items: [
      { id: "api-valuations", label: "POST /v1/valuations" },
      { id: "api-taxonomy", label: "GET /v1/taxonomy" },
      { id: "api-system-status", label: "GET /v1/system/status" },
      { id: "api-feedback", label: "POST /v1/valuations/feedback" },
    ],
  },
  {
    group: "Admin & Governance",
    items: [
      { id: "admin-governance", label: "Admin ML Studio & Model Registry" },
    ],
  },
];

export default function DocsPage() {
  const [activeSection, setActiveSection] = useState("intro");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    const allItemIds = navSections.flatMap((group) => group.items.map((item) => item.id));

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id);
          }
        });
      },
      { rootMargin: "-80px 0px -60% 0px", threshold: 0.1 }
    );

    allItemIds.forEach((id) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, []);

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  const filteredNav = navSections.map((group) => ({
    ...group,
    items: group.items.filter((item) =>
      item.label.toLowerCase().includes(searchQuery.toLowerCase())
    ),
  })).filter((group) => group.items.length > 0);

  return (
    <div className="opencode-docs-container">
      <div className="opencode-docs-grid">
        {/* Left Sticky Sidebar (OpenCode Style) */}
        <aside className="docs-sidebar">
          <div className="docs-search-box">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              type="text"
              className="docs-search-input"
              placeholder="Search documentation..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <nav>
            {filteredNav.map((group) => (
              <div key={group.group}>
                <div className="docs-group-label">{group.group}</div>
                <ul className="docs-nav-list">
                  {group.items.map((item) => (
                    <li key={item.id}>
                      <button
                        type="button"
                        className={`docs-nav-item ${activeSection === item.id ? "active" : ""}`}
                        onClick={() => scrollToSection(item.id)}
                        style={{ width: "100%", textAlign: "left", background: "none", border: "none" }}
                      >
                        <span>{item.label}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </nav>
        </aside>

        {/* Center Main Documentation Pane */}
        <div className="docs-main-pane">
          <div className="docs-header-wrapper">
            <div className="docs-breadcrumbs">
              <Link href="/">CarValue</Link>
              <span>/</span>
              <span>Docs</span>
              <span>/</span>
              <span style={{ color: "var(--accent-primary)" }}>Architecture & Engine</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
              <h1 className="docs-title">Documentation & Engine Guide</h1>
              <span className="pill" style={{ background: "rgba(56, 189, 248, 0.1)", color: "var(--accent-primary)", borderColor: "rgba(56, 189, 248, 0.3)" }}>
                v1.3.3
              </span>
            </div>
            <p className="docs-lead">
              Comprehensive technical guide to the CarValue Alberta Vehicle Intelligence platform. Learn how observation-anchored temporal depreciation, prediction intervals, multi-category taxonomy, and modular architecture power accurate asking-price valuations.
            </p>
          </div>

          {/* Section: Introduction */}
          <section id="intro" className="docs-section">
            <h2 className="docs-section-heading">
              Introduction & Mission
              <a href="#intro" className="heading-anchor">#</a>
            </h2>
            <p className="docs-paragraph">
              <strong>CarValue™</strong> is an explainable asking-price valuation system tailored specifically to Alberta, Canada. Rather than behaving as an opaque black box, every valuation generates a rounded CAD point estimate, an empirical 80% prediction interval, a market evidence confidence rating, and verifiable data provenance.
            </p>

            <div className="docs-card-grid">
              <div className="docs-feature-card">
                <div style={{ color: "var(--accent-primary)", fontWeight: 700, marginBottom: "0.35rem" }}>
                  🎯 Explainable AI
                </div>
                <div style={{ fontSize: "0.84rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                  Centered age OLS benchmarks alongside nonlinear CatBoost regressors, preserving transparent value drivers.
                </div>
              </div>
              <div className="docs-feature-card">
                <div style={{ color: "var(--accent-secondary)", fontWeight: 700, marginBottom: "0.35rem" }}>
                  📊 80% Prediction Band
                </div>
                <div style={{ fontSize: "0.84rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                  Quantile-calibrated bounds (10th to 90th percentile) capturing market dispersion and vehicle condition variance.
                </div>
              </div>
              <div className="docs-feature-card">
                <div style={{ color: "#c084fc", fontWeight: 700, marginBottom: "0.35rem" }}>
                  🛡️ Zero Identity Tracking
                </div>
                <div style={{ fontSize: "0.84rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                  Fully compliant with Alberta PIPA / PIPEDA statutory standards with zero login or personal tracking required.
                </div>
              </div>
            </div>
          </section>

          {/* Section: Unified Architecture */}
          <section id="architecture" className="docs-section">
            <h2 className="docs-section-heading">
              Unified Port 4020 Architecture
              <a href="#architecture" className="heading-anchor">#</a>
            </h2>
            <p className="docs-paragraph">
              The entire system is packaged as a high-performance modular monolith. Client traffic enters exclusively on <strong>Port 4020</strong>, where Next.js serves the frontend UI and seamlessly proxies internal API calls to the FastAPI machine learning backend on loopback port 8042.
            </p>

            <CodeBlock
              tabs={[
                {
                  label: "Architecture Diagram",
                  language: "text",
                  code: `               User Browser / Client
                         │
                         ▼
        ┌──────────────────────────────────┐
        │       Unified Port: 4020         │
        │     (Next.js App & Proxy)        │
        └────────────────┬─────────────────┘
                         │
         ┌───────────────┴───────────────┐
         │ (Internal Next.js Rewrites)   │
         ▼                               ▼
  Frontend Pages                   FastAPI Backend
  (/, /docs, /admin, /privacy)    (Internal :8042)
                                  (/api/v1/*, /api/admin/*)`,
                },
                {
                  label: "Quickstart Launcher",
                  language: "bash",
                  code: `# Launch full CarValue application stack on port 4020
bash bin/start

# Run complete pytest test suite (90/90 tests passing)
.venv/bin/pytest -v`,
                },
              ]}
            />
          </section>

          {/* Section: Observation-Anchored Age */}
          <section id="price-aging" className="docs-section">
            <h2 className="docs-section-heading">
              Observation-Anchored Age Calculation
              <a href="#price-aging" className="heading-anchor">#</a>
            </h2>
            <p className="docs-paragraph">
              When training on historical inventory datasets (such as 2022 dealer listings), calculating vehicle age relative to runtime <code>today()</code> produces a critical temporal anchor flaw. A 2021 vehicle listed in 2022 was <strong>1.0 year old</strong> at observation. If trained with a 2026 anchor (5.0 years old), the model learns that a 5-year-old vehicle is worth 2022 prices.
            </p>

            <div className="docs-callout docs-callout-note">
              <div className="docs-callout-icon">💡</div>
              <div>
                <strong>Temporal Separation Formula:</strong>
                <br />
                During training: <code style={{ color: "var(--accent-primary)" }}>Age_obs = vehicle_age_years(model_year, observed_at)</code>
                <br />
                During runtime valuation: <code style={{ color: "var(--accent-primary)" }}>Age_val = vehicle_age_years(model_year, valuation_date)</code>
              </div>
            </div>

            <p className="docs-paragraph">
              This enables the machine learning model to learn the true empirical depreciation rate <code>f(Age, Mileage, Trim, Drivetrain)</code> and correctly devalue vehicles over time.
            </p>
          </section>

          {/* Section: Macro Price Drift */}
          <section id="macro-drift" className="docs-section">
            <h2 className="docs-section-heading">
              Macro Price Drift & Year Adjustment
              <a href="#macro-drift" className="heading-anchor">#</a>
            </h2>
            <p className="docs-paragraph">
              In addition to vehicle age depreciation, macro economic factors (inflation, supply constraints, consumer price index shifts) impact used vehicle prices across multi-year spans:
            </p>

            <CodeBlock
              tabs={[
                {
                  label: "Economics Formula",
                  language: "python",
                  code: `# Macro price drift compound adjustment
years_elapsed = (valuation_date - observation_date).days / 365.25
adjusted_price = base_model_estimate * ((1.0 + annual_drift_rate) ** years_elapsed)`,
                },
              ]}
            />
          </section>

          {/* Section: Statistical Models */}
          <section id="statistical-models" className="docs-section">
            <h2 className="docs-section-heading">
              OLS Baseline & CatBoost ML Regressors
              <a href="#statistical-models" className="heading-anchor">#</a>
            </h2>
            <p className="docs-paragraph">
              CarValue implements a multi-model evaluation strategy:
            </p>

            <ol className="docs-steps">
              <li className="docs-step-item">
                <strong style={{ color: "var(--text-primary)" }}>Centered OLS Baseline:</strong>
                <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: "0.25rem" }}>
                  A transparent linear regression model where model year is centered to the valuation date. Retained as a reproducible baseline with transparent coefficients.
                </p>
              </li>
              <li className="docs-step-item">
                <strong style={{ color: "var(--text-primary)" }}>CatBoost Nonlinear Candidate:</strong>
                <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: "0.25rem" }}>
                  Gradient boosted decision trees handling nonlinear mileage decay curves, categorical trim interactions, and missing feature imputation.
                </p>
              </li>
              <li className="docs-step-item">
                <strong style={{ color: "var(--text-primary)" }}>Chronological Holdout Validation:</strong>
                <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: "0.25rem" }}>
                  Data splits are strictly temporal to prevent data leakage and evaluate real-world forecasting accuracy (MdAPE ≤ 12% target).
                </p>
              </li>
            </ol>
          </section>

          {/* Section: Prediction Intervals */}
          <section id="prediction-intervals" className="docs-section">
            <h2 className="docs-section-heading">
              80% Empirical Prediction Intervals
              <a href="#prediction-intervals" className="heading-anchor">#</a>
            </h2>
            <p className="docs-paragraph">
              Rather than providing an illusory exact point estimate, CarValue calculates residual quantiles (10th percentile and 90th percentile) to construct an <strong>80% prediction interval</strong>:
            </p>

            <div className="docs-callout docs-callout-tip">
              <div className="docs-callout-icon">🎯</div>
              <div>
                <strong>Interval Interpretation:</strong> 80% of verified Alberta dealer listings for the given make, model, year, and mileage fall within the displayed range. The spread accounts for vehicle condition, optional equipment, and dealer pricing variance.
              </div>
            </div>
          </section>

          {/* Section: Refusal Rules */}
          <section id="refusal-rules" className="docs-section">
            <h2 className="docs-section-heading">
              Explainable Refusal & Insufficient Data Rules
              <a href="#refusal-rules" className="heading-anchor">#</a>
            </h2>
            <p className="docs-paragraph">
              In accordance with product guardrails, CarValue refuses to fabricate precision when market data is insufficient. A request returns <code>Insufficient Data</code> if:
            </p>
            <ul style={{ color: "var(--text-secondary)", fontSize: "0.9rem", lineHeight: 1.8, paddingLeft: "1.25rem" }}>
              <li>Fewer than <strong>4 comparable listings</strong> exist in the Alberta database.</li>
              <li>Vehicle mileage or model year falls outside calibrated training bounds.</li>
              <li>The vehicle make/model combination has not passed segment validation gates.</li>
            </ul>
          </section>

          {/* Section: Multi-Category Expansion (M9) */}
          <section id="categories" className="docs-section">
            <h2 className="docs-section-heading">
              All Alberta Vehicle Categories (Milestone M9)
              <a href="#categories" className="heading-anchor">#</a>
            </h2>
            <p className="docs-paragraph">
              Milestone M9 expanded the engine from pickups to all 7 primary market categories, indexing over <strong>44,412 real Alberta vehicle listings</strong>:
            </p>

            <div className="docs-card-grid">
              <div className="docs-feature-card">
                <div style={{ fontWeight: 700, color: "var(--text-primary)" }}>🛻 Pickups (7,642)</div>
                <div style={{ fontSize: "0.82rem", color: "var(--text-secondary)", marginTop: "0.25rem" }}>
                  F-150, Super Duty, Ram 1500/2500/3500, Silverado, Sierra, Tacoma, Tundra, Ranger
                </div>
              </div>
              <div className="docs-feature-card">
                <div style={{ fontWeight: 700, color: "var(--text-primary)" }}>🚙 SUVs & Crossovers (21,890)</div>
                <div style={{ fontSize: "0.82rem", color: "var(--text-secondary)", marginTop: "0.25rem" }}>
                  Escape, Explorer, RAV4, Highlander, Grand Cherokee, CR-V, Santa Fe, Tucson, Equinox, Tiguan
                </div>
              </div>
              <div className="docs-feature-card">
                <div style={{ fontWeight: 700, color: "var(--text-primary)" }}>🚗 Sedans (7,631)</div>
                <div style={{ fontSize: "0.82rem", color: "var(--text-secondary)", marginTop: "0.25rem" }}>
                  Civic, Camry, Corolla, Elantra, Cruze, Sentra, Jetta, 3 Series, A4, Accord
                </div>
              </div>
              <div className="docs-feature-card">
                <div style={{ fontWeight: 700, color: "var(--text-primary)" }}>🏎️ Coupes & Sports (1,243)</div>
                <div style={{ fontSize: "0.82rem", color: "var(--text-secondary)", marginTop: "0.25rem" }}>
                  Mustang, Camaro, Corvette, Challenger, 4 Series, 2 Series, GR86, BRZ
                </div>
              </div>
              <div className="docs-feature-card">
                <div style={{ fontWeight: 700, color: "var(--text-primary)" }}>🚐 Vans & Minivans (2,006)</div>
                <div style={{ fontSize: "0.82rem", color: "var(--text-secondary)", marginTop: "0.25rem" }}>
                  Grand Caravan, Pacifica, Town & Country, Odyssey, Sienna, Transit
                </div>
              </div>
              <div className="docs-feature-card">
                <div style={{ fontWeight: 700, color: "var(--text-primary)" }}>🚘 Hatchbacks (3,177)</div>
                <div style={{ fontSize: "0.82rem", color: "var(--text-secondary)", marginTop: "0.25rem" }}>
                  Golf / GTI / Golf R, Mazda3, Elantra GT, Soul, Civic Hatchback
                </div>
              </div>
            </div>
          </section>

          {/* Section: Alberta Regions */}
          <section id="alberta-regions" className="docs-section">
            <h2 className="docs-section-heading">
              Alberta Regional Sub-Market Segmentation
              <a href="#alberta-regions" className="heading-anchor">#</a>
            </h2>
            <p className="docs-paragraph">
              Vehicle pricing exhibits distinct geographic sub-market premiums across Alberta. The engine segments geographic evidence into 8 distinct zones:
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginTop: "0.75rem" }}>
              {[
                "Calgary Region",
                "Edmonton Region",
                "Red Deer Central",
                "Lethbridge South",
                "Medicine Hat Southeast",
                "Fort McMurray North",
                "Grande Prairie Peace",
                "Rural Alberta",
              ].map((r) => (
                <span key={r} className="pill" style={{ fontSize: "0.8rem" }}>
                  📍 {r}
                </span>
              ))}
            </div>
          </section>

          {/* Section: API Valuations */}
          <section id="api-valuations" className="docs-section">
            <h2 className="docs-section-heading">
              POST /v1/valuations
              <a href="#api-valuations" className="heading-anchor">#</a>
            </h2>
            <p className="docs-paragraph">
              Execute an explainable asking-price valuation for any supported Alberta vehicle:
            </p>

            <CodeBlock
              tabs={[
                {
                  label: "cURL",
                  language: "bash",
                  code: `curl -X POST http://localhost:4020/api/v1/valuations \\
  -H "Content-Type: application/json" \\
  -d '{
    "make": "Toyota",
    "model": "RAV4",
    "year": 2021,
    "mileage_km": 45000,
    "trim": "XLE",
    "drivetrain": "4wd",
    "seller_type": "dealer",
    "category": "suv",
    "dataset_filter": "real_only"
  }'`,
                },
                {
                  label: "Response JSON",
                  language: "json",
                  code: `{
  "estimate_cad": 28900,
  "interval_low_cad": 24300,
  "interval_high_cad": 34600,
  "confidence_label": "high",
  "comparables_count": 438,
  "real_comparables_count": 438,
  "synthetic_comparables_count": 0,
  "dataset_provenance": "Real Alberta Dealer Listings (2022 Dataset)",
  "category": "suv",
  "data_freshness_days": 8.0,
  "valuation_date": "2026-08-28",
  "disclaimer": "This is an estimate, not a professional appraisal."
}`,
                },
                {
                  label: "TypeScript Client",
                  language: "typescript",
                  code: `import { ValuationRequest, ValuationResponse } from "@/lib/types";

const res = await fetch("/api/v1/valuations", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    make: "Ford",
    model: "F-150",
    year: 2021,
    mileage_km: 60000,
    drivetrain: "4wd",
    seller_type: "dealer"
  })
});
const data: ValuationResponse = await res.json();
console.log(\`Estimated: $\${data.estimate_cad} CAD\`);`,
                },
              ]}
            />
          </section>

          {/* Section: API Taxonomy */}
          <section id="api-taxonomy" className="docs-section">
            <h2 className="docs-section-heading">
              GET /v1/taxonomy
              <a href="#api-taxonomy" className="heading-anchor">#</a>
            </h2>
            <p className="docs-paragraph">
              Retrieve all canonical vehicle makes, models categorized across market segments (pickups, SUVs, sedans, coupes, vans, hatchbacks), available trims, and drivetrains.
            </p>

            <CodeBlock
              tabs={[
                {
                  label: "cURL",
                  language: "bash",
                  code: `curl -X GET http://localhost:4020/api/v1/taxonomy`,
                },
                {
                  label: "Response JSON",
                  language: "json",
                  code: `{
  "makes": ["Ford", "Toyota", "Ram", "Chevrolet", "GMC", "Honda", "Hyundai", "Jeep", ...],
  "models_by_make": {
    "Ford": ["F-150", "Super Duty F-250", "Ranger", "Escape", "Explorer", "Mustang", "Edge"],
    "Toyota": ["Tacoma", "Tundra", "RAV4", "Highlander", "Camry", "Corolla", "4Runner"],
    "Ram": ["1500", "2500", "3500", "1500 Classic", "ProMaster"]
  },
  "trims_by_model": {
    "F-150": ["XL", "XLT", "Lariat", "King Ranch", "Platinum", "Limited", "Tremor", "Raptor"],
    "RAV4": ["LE", "XLE", "Trail", "Limited", "TRD Off-Road", "XSE Prime"]
  },
  "categories": ["pickup", "suv", "sedan", "hatchback", "van", "coupe", "wagon", "all"],
  "models_by_category": {
    "pickup": {
      "Ford": ["F-150", "Super Duty F-250", "Ranger"],
      "Toyota": ["Tacoma", "Tundra"]
    }
  }
}`,
                },
                {
                  label: "TypeScript Client",
                  language: "typescript",
                  code: `const res = await fetch("/api/v1/taxonomy");
const taxonomy = await res.json();
console.log("Available categories:", taxonomy.categories);`,
                },
              ]}
            />
          </section>

          {/* Section: API System Status */}
          <section id="api-system-status" className="docs-section">
            <h2 className="docs-section-heading">
              GET /v1/system/status
              <a href="#api-system-status" className="heading-anchor">#</a>
            </h2>
            <p className="docs-paragraph">
              Inspect live backend health, active machine learning model metadata, training sample count, total indexed listings, price observations, and data freshness metrics.
            </p>

            <CodeBlock
              tabs={[
                {
                  label: "cURL",
                  language: "bash",
                  code: `curl -X GET http://localhost:4020/api/v1/system/status`,
                },
                {
                  label: "Response JSON",
                  language: "json",
                  code: `{
  "status": "ok",
  "timestamp_utc": "2026-08-28T12:00:00.000000+00:00",
  "active_model": {
    "id": 4,
    "algorithm": "catboost_candidate",
    "trained_at_utc": "2026-08-25T18:37:43.635130+00:00",
    "metrics": {
      "training_samples": 44420,
      "algorithm": "catboost_candidate",
      "note": "Observation-anchored temporal training on Alberta market data"
    }
  },
  "data_freshness_days": 8.0,
  "total_listings": 44412,
  "total_price_observations": 44420,
  "sources_breakdown": {
    "real_dealer_listings_2022": 44356,
    "synthetic_simulator_sample": 56
  }
}`,
                },
                {
                  label: "TypeScript Client",
                  language: "typescript",
                  code: `const res = await fetch("/api/v1/system/status");
const status = await res.json();
console.log(\`Active Model: \${status.active_model.algorithm} (ID: \${status.active_model.id})\`);`,
                },
              ]}
            />
          </section>

          {/* Section: API Valuation Feedback */}
          <section id="api-feedback" className="docs-section">
            <h2 className="docs-section-heading">
              POST /v1/valuations/feedback
              <a href="#api-feedback" className="heading-anchor">#</a>
            </h2>
            <p className="docs-paragraph">
              Submit anonymous feedback regarding valuation usefulness or market calibration accuracy. Feedback helps fine-tune uncertainty bounds without collecting any user identity or personal data.
            </p>

            <CodeBlock
              tabs={[
                {
                  label: "cURL",
                  language: "bash",
                  code: `curl -X POST http://localhost:4020/api/v1/valuations/feedback \\
  -H "Content-Type: application/json" \\
  -d '{
    "valuation_event_id": 142,
    "feedback_useful": true,
    "feedback_notes": "Close to recent Calgary dealer trade-in quote."
  }'`,
                },
                {
                  label: "Response JSON",
                  language: "json",
                  code: `{
  "status": "ok",
  "message": "Feedback recorded"
}`,
                },
                {
                  label: "TypeScript Client",
                  language: "typescript",
                  code: `await fetch("/api/v1/valuations/feedback", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    valuation_event_id: 142,
    feedback_useful: true,
    feedback_notes: "Accurate interval."
  })
});`,
                },
              ]}
            />
          </section>

          {/* Section: Admin ML Studio & Model Registry */}
          <section id="admin-governance" className="docs-section">
            <h2 className="docs-section-heading">
              Admin ML Studio & Model Registry
              <a href="#admin-governance" className="heading-anchor">#</a>
            </h2>
            <p className="docs-paragraph">
              Authorized administrators can access the <strong>Admin & ML Studio</strong> (<code>/admin</code>) to monitor system health, inspect dataset snapshots, adjust macro inflation drift parameters, and promote candidate models:
            </p>

            <div className="docs-card-grid">
              <div className="docs-feature-card">
                <div style={{ color: "var(--accent-primary)", fontWeight: 700 }}>🎛️ Hyperparameter Sliders</div>
                <div style={{ fontSize: "0.83rem", color: "var(--text-secondary)", marginTop: "0.3rem" }}>
                  Live adjustment of annual price drift rate (default 2.5%/year) and refusal thresholds.
                </div>
              </div>
              <div className="docs-feature-card">
                <div style={{ color: "var(--accent-emerald)", fontWeight: 700 }}>🏷️ Segment Regression Gates</div>
                <div style={{ fontSize: "0.83rem", color: "var(--text-secondary)", marginTop: "0.3rem" }}>
                  Automated checks preventing promotion if any make/model segment regresses by &gt;8% MAE.
                </div>
              </div>
              <div className="docs-feature-card">
                <div style={{ color: "#c084fc", fontWeight: 700 }}>🔄 1-Click Rollback</div>
                <div style={{ fontSize: "0.83rem", color: "var(--text-secondary)", marginTop: "0.3rem" }}>
                  Instantly revert active production model references to any previously verified artifact.
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
