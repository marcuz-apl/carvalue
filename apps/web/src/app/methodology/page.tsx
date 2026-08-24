import React from "react";

export default function MethodologyPage() {
  return (
    <div style={{ maxWidth: "800px", margin: "0 auto", padding: "1rem 0" }}>
      <h1 className="hero-title" style={{ fontSize: "2.25rem", marginBottom: "1rem" }}>
        Valuation Methodology & Model Governance
      </h1>

      <p className="hero-subtitle" style={{ marginBottom: "2rem" }}>
        CarValue provides explainable, reproducible asking-price estimates built on transparent statistical principles for the Alberta pickup market.
      </p>

      <div className="glass-card" style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "1.25rem", color: "var(--accent-primary)", marginBottom: "0.75rem" }}>
          1. Centered-Age Reference Baseline
        </h2>
        <p style={{ color: "var(--text-secondary)", lineHeight: 1.6, fontSize: "0.95rem" }}>
          Unlike black-box models with uninterpretable calendar-year intercepts, our baseline models center vehicle age relative to the exact reference valuation date:
        </p>
        <div
          style={{
            background: "var(--bg-surface-elevated)",
            padding: "1rem",
            borderRadius: "var(--radius-md)",
            margin: "1rem 0",
            fontFamily: "monospace",
            fontSize: "0.9rem",
            color: "var(--accent-primary)",
          }}
        >
          AskingPrice (CAD) = β₀ + β₁ · (Age - MeanAge) + β₂ · MileageKm
        </div>
      </div>

      <div className="glass-card" style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "1.25rem", color: "var(--accent-primary)", marginBottom: "0.75rem" }}>
          2. CatBoost Quantile Regressions (80% Prediction Intervals)
        </h2>
        <p style={{ color: "var(--text-secondary)", lineHeight: 1.6, fontSize: "0.95rem" }}>
          Our production candidate models utilize gradient boosted trees (CatBoost) with dual quantile loss functions (α = 0.10 and α = 0.90) to capture nonlinear market depreciation, trim step-ups, and drivetrain premiums without assuming normal error distributions.
        </p>
      </div>

      <div className="glass-card" style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "1.25rem", color: "var(--accent-primary)", marginBottom: "0.75rem" }}>
          3. Explainable Refusal Rules
        </h2>
        <p style={{ color: "var(--text-secondary)", lineHeight: 1.6, fontSize: "0.95rem" }}>
          We prefer <em>&quot;Insufficient Data&quot;</em> to fabricated precision. If an input configuration has fewer than 4 recent Alberta comparables, or if the odometer / year values are outside calibrated model bounds, the system refuses to guess and explains the reason clearly.
        </p>
      </div>
    </div>
  );
}
