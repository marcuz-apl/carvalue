"use client";

import React, { useState } from "react";
import { ValuationRequest, ValuationResponse } from "../lib/types";

interface ValuationResultProps {
  result: ValuationResponse;
  request: ValuationRequest;
}

export default function ValuationResult({
  result,
  request,
}: ValuationResultProps) {
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);

  const confidenceClass =
    result.confidence_label === "high"
      ? "badge-high"
      : result.confidence_label === "medium"
      ? "badge-medium"
      : "badge-low";

  const confidenceText =
    result.confidence_label === "high"
      ? "High Market Confidence"
      : result.confidence_label === "medium"
      ? "Moderate Confidence"
      : "Low Sample Confidence";

  return (
    <div className="glass-card result-card" id="valuation-result-container">
      <div>
        <div className="result-header">
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
            }}
          >
            <div>
              <span className="pill badge-high" style={{ marginBottom: "0.5rem" }}>
                Alberta Market Estimate
              </span>
              <h2
                className="result-vehicle-name"
                style={{ fontSize: "1.35rem", color: "var(--text-primary)" }}
              >
                {request.year} {request.make} {request.model} {request.trim || ""}
              </h2>
              <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
                {Number(request.mileage_km).toLocaleString()} km • {request.drivetrain?.toUpperCase() || "4WD"} •{" "}
                {request.seller_type === "dealer" ? "Dealer" : "Private"}
              </div>
            </div>

            <span className={`pill ${confidenceClass}`} id="confidence-badge">
              {confidenceText}
            </span>
          </div>
        </div>

        {/* Asking Price Highlight Box */}
        <div className="result-price-box">
          <div className="result-label">Asking-Price Estimate</div>
          <div className="result-price" id="text-estimate-cad">
            ${result.estimate_cad.toLocaleString()}
            <span className="result-currency">CAD</span>
          </div>
        </div>

        {/* 80% Prediction Interval */}
        <div className="interval-container" id="interval-container">
          <div className="interval-header">
            <span>80% Prediction Interval</span>
            <span style={{ color: "var(--accent-primary)" }}>
              ${result.interval_low_cad.toLocaleString()} – ${result.interval_high_cad.toLocaleString()} CAD
            </span>
          </div>

          <div className="interval-bar-track">
            <div className="interval-bar-fill" />
          </div>

          <div className="interval-bounds">
            <span>10th Percentile (Low)</span>
            <span>90th Percentile (High)</span>
          </div>
        </div>

        {/* Evidence & Freshness Meta Pills */}
        <div className="meta-pills">
          <span className="pill" id="pill-comparables-count">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
            {result.comparables_count} Alberta Comparables
          </span>

          <span className="pill" id="pill-data-freshness">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            {result.data_freshness_days <= 1
              ? "Updated Today"
              : `Updated ${result.data_freshness_days} days ago`}
          </span>

          <span className="pill">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
              <line x1="16" y1="2" x2="16" y2="6" />
              <line x1="8" y1="2" x2="8" y2="6" />
              <line x1="3" y1="10" x2="21" y2="10" />
            </svg>
            Valuation: {result.valuation_date}
          </span>
        </div>
      </div>

      <div>
        {/* User Feedback Widget */}
        <div className="feedback-section" id="feedback-widget">
          <span>Was this estimate helpful?</span>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              type="button"
              id="btn-feedback-useful"
              className={`feedback-btn ${feedback === "up" ? "active" : ""}`}
              onClick={() => setFeedback("up")}
            >
              👍 Yes
            </button>
            <button
              type="button"
              id="btn-feedback-not-useful"
              className={`feedback-btn ${feedback === "down" ? "active" : ""}`}
              onClick={() => setFeedback("down")}
            >
              👎 No
            </button>
          </div>
        </div>

        {/* Mandatory Legal Disclaimer */}
        <div className="legal-disclaimer" id="legal-disclaimer">
          <strong>Mandatory Notice:</strong> {result.disclaimer} This asking-price estimate is generated using calibrated Alberta market data and does not constitute a guaranteed trade-in offer, binding purchase price, or certified professional appraisal.
        </div>
      </div>
    </div>
  );
}
