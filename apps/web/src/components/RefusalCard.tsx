"use client";

import React from "react";
import { ValuationRequest } from "../lib/types";

interface RefusalCardProps {
  request: ValuationRequest;
  onReset?: () => void;
}

export default function RefusalCard({ request, onReset }: RefusalCardProps) {
  return (
    <div
      className="glass-card result-card"
      id="refusal-card-container"
      style={{ borderColor: "rgba(245, 158, 11, 0.4)" }}
    >
      <div>
        <div className="result-header">
          <span className="pill badge-refusal" id="refusal-badge" style={{ marginBottom: "0.5rem" }}>
            Refusal Policy Triggered
          </span>
          <h2
            className="result-vehicle-name"
            style={{ fontSize: "1.35rem", color: "var(--text-primary)" }}
          >
            {request.year} {request.make} {request.model} {request.trim || ""}
          </h2>
        </div>

        <div
          style={{
            background: "rgba(245, 158, 11, 0.08)",
            border: "1px solid rgba(245, 158, 11, 0.25)",
            borderRadius: "var(--radius-md)",
            padding: "1.5rem",
            margin: "1.5rem 0",
          }}
        >
          <h3
            style={{
              color: "var(--accent-amber)",
              fontSize: "1.1rem",
              fontWeight: 700,
              marginBottom: "0.5rem",
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            Insufficient Market Evidence
          </h3>
          <p style={{ fontSize: "0.9rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
            Per our explainability and product integrity guidelines, CarValue refuses to fabricate an asking-price estimate when representative Alberta pickup data is sparse ($&lt;4$ comparables), out-of-distribution, or unsupported.
          </p>
        </div>

        <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", lineHeight: 1.6 }}>
          <strong>Possible reasons:</strong>
          <ul style={{ paddingLeft: "1.25rem", marginTop: "0.25rem" }}>
            <li>Fewer than 4 recent comparable listings exist in Alberta for this specific trim and year.</li>
            <li>Odometer reading ({Number(request.mileage_km).toLocaleString()} km) is outside calibrated model training bounds.</li>
            <li>Vehicle model is outside the Alberta used-pickup scope (2010–2025).</li>
          </ul>
        </div>
      </div>

      <div style={{ marginTop: "2rem" }}>
        {onReset && (
          <button
            type="button"
            onClick={onReset}
            className="submit-btn"
            style={{ background: "var(--bg-surface-elevated)", color: "var(--text-primary)" }}
          >
            Adjust Vehicle Parameters
          </button>
        )}
        <div className="legal-disclaimer" style={{ marginTop: "1rem" }}>
          CarValue Alberta does not guess or interpolate prices for sparse market segments.
        </div>
      </div>
    </div>
  );
}
