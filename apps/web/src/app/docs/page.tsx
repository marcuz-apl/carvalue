import type { Metadata } from "next";
import Link from "next/link";
import React from "react";

export const metadata: Metadata = {
  title: "Documentation & Methodology | CarValue Alberta",
  description:
    "Comprehensive documentation of valuation algorithms, price aging economics, Alberta market calibration, and data governance.",
};

export default function DocsPage() {
  return (
    <div style={{ maxWidth: "880px", margin: "0 auto", padding: "1.5rem 1rem" }}>
      {/* Header */}
      <div style={{ marginBottom: "2.5rem" }}>
        <Link
          href="/"
          style={{
            fontSize: "0.85rem",
            color: "var(--accent-primary)",
            display: "inline-flex",
            alignItems: "center",
            gap: "0.35rem",
            marginBottom: "1rem",
            textDecoration: "none",
          }}
        >
          ← Back to Valuator
        </Link>
        <h1 style={{ fontSize: "2.25rem", fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
          Documentation & Governance
        </h1>
        <p style={{ fontSize: "1.05rem", color: "var(--text-secondary)", marginTop: "0.5rem", lineHeight: 1.6 }}>
          Technical specifications, price aging mechanics, statistical interval calibration, and ethical data standards for the CarValue Alberta used-pickup engine.
        </p>
      </div>

      {/* Section 1: Price Aging & Year Drift Economics */}
      <section className="glass-card" style={{ padding: "2rem", marginBottom: "2rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1.25rem" }}>
          <div
            style={{
              padding: "0.5rem",
              borderRadius: "0.5rem",
              background: "rgba(56, 189, 248, 0.15)",
              color: "var(--accent-primary)",
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
          </div>
          <h2 style={{ fontSize: "1.35rem", fontWeight: 700, margin: 0 }}>
            1. Price Aging & Macro Inflation Economics
          </h2>
        </div>

        <p style={{ color: "var(--text-secondary)", lineHeight: 1.7, marginBottom: "1rem" }}>
          A fundamental question in automotive valuation is: <em>If a dataset consists of historical vehicle listings (e.g., recorded in 2022), how does the system generate accurate market predictions for the current valuation year (2026)?</em>
        </p>

        <p style={{ color: "var(--text-secondary)", lineHeight: 1.7, marginBottom: "1.5rem" }}>
          CarValue models two distinct time-dependent economic forces:
        </p>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem", marginBottom: "1.5rem" }}>
          <div
            style={{
              background: "rgba(255, 255, 255, 0.03)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              borderRadius: "0.75rem",
              padding: "1.25rem",
            }}
          >
            <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--accent-primary)", marginBottom: "0.5rem" }}>
              A. Vehicle Age Depreciation Curve
            </h3>
            <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
              Vehicles do not depreciate by calendar date; they depreciate by <strong>vehicle age at the time of valuation</strong>:
              <br />
              <code style={{ background: "rgba(0,0,0,0.3)", padding: "0.15rem 0.4rem", borderRadius: "4px", display: "inline-block", marginTop: "0.35rem" }}>
                Vehicle Age = Valuation Year - Model Year
              </code>
              <br />
              A 2021 Ford F-150 evaluated in 2026 has a vehicle age of 5 years. The model applies the 5-year empirical depreciation coefficient learned across 7,000+ Alberta pickup observations.
            </p>
          </div>

          <div
            style={{
              background: "rgba(255, 255, 255, 0.03)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              borderRadius: "0.75rem",
              padding: "1.25rem",
            }}
          >
            <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--accent-emerald)", marginBottom: "0.5rem" }}>
              B. Macro Market Price Drift & CPI
            </h3>
            <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
              Between 2022 and 2026, baseline Canadian automotive price levels shifted due to macro inflation and supply chain dynamics:
              <br />
              <code style={{ background: "rgba(0,0,0,0.3)", padding: "0.15rem 0.4rem", borderRadius: "4px", display: "inline-block", marginTop: "0.35rem" }}>
                Drift Adj = Price × (1 + Annual_Drift_Rate)^(ΔYears)
              </code>
              <br />
              Administrators can configure the annual macro price drift index in the Admin Studio to calibrate historical listing baselines to current purchasing power.
            </p>
          </div>
        </div>
      </section>

      {/* Section 2: Mathematical Baseline & Uncertainty Intervals */}
      <section className="glass-card" style={{ padding: "2rem", marginBottom: "2rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1.25rem" }}>
          <div
            style={{
              padding: "0.5rem",
              borderRadius: "0.5rem",
              background: "rgba(16, 185, 129, 0.15)",
              color: "var(--accent-emerald)",
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="20" x2="18" y2="10" />
              <line x1="12" y1="20" x2="12" y2="4" />
              <line x1="6" y1="20" x2="6" y2="14" />
            </svg>
          </div>
          <h2 style={{ fontSize: "1.35rem", fontWeight: 700, margin: 0 }}>
            2. Statistical Modeling & 80% Prediction Intervals
          </h2>
        </div>

        <p style={{ color: "var(--text-secondary)", lineHeight: 1.7, marginBottom: "1rem" }}>
          CarValue strictly adheres to an <strong>explainable modeling approach</strong>. Rather than using opaque black-box deep nets, the core baseline estimates value through centered Ordinary Least Squares (OLS) with calibrated quantile prediction intervals:
        </p>

        <div
          style={{
            background: "rgba(0, 0, 0, 0.4)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            borderRadius: "0.75rem",
            padding: "1.25rem",
            fontFamily: "var(--font-mono, monospace)",
            fontSize: "0.85rem",
            color: "var(--text-primary)",
            marginBottom: "1.25rem",
            overflowX: "auto",
          }}
        >
          Price_CAD = β₀ + β₁ × (Valuation_Year - Model_Year) + β₂ × Mileage_km + β_trim + β_drivetrain + ε
        </div>

        <ul style={{ color: "var(--text-secondary)", lineHeight: 1.8, paddingLeft: "1.25rem", fontSize: "0.9rem" }}>
          <li>
            <strong>Centered Vehicle Age:</strong> Age is centered relative to the valuation date, avoiding uninterpretable raw-year regression intercepts.
          </li>
          <li>
            <strong>80% Empirical Prediction Interval:</strong> We compute residual quantiles (10th percentile to 90th percentile) to bound market uncertainty. 80% of verified dealer listings fall within this band.
          </li>
          <li>
            <strong>Conservative Refusal ("Insufficient Data"):</strong> The system explicitly refuses to guess when comparables count &lt; 4 or vehicle parameters exceed calibrated market support.
          </li>
        </ul>
      </section>

      {/* Section 3: Data Provenance & Ethics */}
      <section className="glass-card" style={{ padding: "2rem", marginBottom: "2rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1.25rem" }}>
          <div
            style={{
              padding: "0.5rem",
              borderRadius: "0.5rem",
              background: "rgba(167, 139, 250, 0.15)",
              color: "#c084fc",
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
          </div>
          <h2 style={{ fontSize: "1.35rem", fontWeight: 700, margin: 0 }}>
            3. Data Acquisition & Alberta Privacy Guardrails
          </h2>
        </div>

        <p style={{ color: "var(--text-secondary)", lineHeight: 1.7, marginBottom: "1rem" }}>
          CarValue operates under strict Canadian and Alberta privacy principles (FOIP / PIPA compliance):
        </p>

        <ul style={{ color: "var(--text-secondary)", lineHeight: 1.8, paddingLeft: "1.25rem", fontSize: "0.9rem" }}>
          <li>
            <strong>Deny-by-Default Ingestion:</strong> Automated scrapers for unauthorized platforms (e.g. AutoTrader, CarGurus) are disabled by default. Data is sourced through authorized DMS feeds, open datasets, and permitted dealer feeds.
          </li>
          <li>
            <strong>No User Tracking:</strong> Zero user registration or personal identity collection is required to evaluate a vehicle.
          </li>
          <li>
            <strong>No Private Seller PII:</strong> Names, phone numbers, email addresses, and personal listing descriptions are never stored in the database.
          </li>
        </ul>
      </section>

      {/* Section 4: Mandatory Legal Disclaimer */}
      <section className="glass-card" id="disclaimer" style={{ padding: "2rem", borderLeft: "4px solid var(--accent-amber)" }}>
        <h2 style={{ fontSize: "1.15rem", fontWeight: 700, color: "var(--accent-amber)", marginBottom: "0.75rem" }}>
          Mandatory Consumer Notice & Disclaimer
        </h2>
        <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>
          CarValue provides an <strong>asking-price market estimate</strong> based on statistical regression of historical Alberta dealer listings. It does not constitute a certified appraisal, guaranteed trade-in offer, binding purchase agreement, or warranty of mechanical condition. Actual transaction prices depend on physical inspection, vehicle history report (Carfax/ICBC), accident records, mechanical condition, and individual negotiations.
        </p>
      </section>
    </div>
  );
}
