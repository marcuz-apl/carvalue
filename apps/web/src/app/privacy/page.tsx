import Link from "next/link";
import React from "react";

export default function PrivacyPage() {
  return (
    <div style={{ maxWidth: "800px", margin: "0 auto", padding: "1rem 0" }}>
      {/* Return to App Breadcrumb */}
      <div style={{ marginBottom: "1.25rem" }}>
        <Link
          href="/"
          id="btn-privacy-back-top"
          className="footer-pill-btn hover-accent"
          style={{ display: "inline-flex", gap: "0.5rem", alignItems: "center" }}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="19" y1="12" x2="5" y2="12" />
            <polyline points="12 19 5 12 12 5" />
          </svg>
          <span>Return to Valuation App</span>
        </Link>
      </div>

      <h1 className="hero-title" style={{ fontSize: "2.25rem", marginBottom: "1rem" }}>
        Data Rights & Privacy Policy
      </h1>

      <p className="hero-subtitle" style={{ marginBottom: "2rem" }}>
        CarValue is designed with privacy-by-default and strict data ethics under Alberta and Canadian privacy principles (PIPA / PIPEDA).
      </p>

      <div className="glass-card" style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "1.25rem", color: "var(--accent-secondary)", marginBottom: "0.75rem" }}>
          1. Zero Personal Data Collected for Valuations
        </h2>
        <p style={{ color: "var(--text-secondary)", lineHeight: 1.6, fontSize: "0.95rem" }}>
          You are never required to enter your name, email address, phone number, location GPS, or create an account merely to obtain an asking-price estimate. Valuations are 100% accessible to the public anonymously.
        </p>
      </div>

      <div className="glass-card" style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "1.25rem", color: "var(--accent-secondary)", marginBottom: "0.75rem" }}>
          2. Deny-by-Default Data Acquisition Policy
        </h2>
        <p style={{ color: "var(--text-secondary)", lineHeight: 1.6, fontSize: "0.95rem" }}>
          Automated collection runs strictly through authorized and licensed sources. We never bypass logins, paywalls, CAPTCHAs, or robots.txt directives, and we never collect seller contact details, personal comments, or vehicle photos.
        </p>
      </div>

      <div className="glass-card" style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "1.25rem", color: "var(--accent-secondary)", marginBottom: "0.75rem" }}>
          3. Privacy-Minimized Telemetry
        </h2>
        <p style={{ color: "var(--text-secondary)", lineHeight: 1.6, fontSize: "0.95rem" }}>
          Product telemetry captures only coarse aggregate metrics (response latency in ms, vehicle configuration, device class) with zero persistent visitor fingerprinting or IP tracking.
        </p>
      </div>

      {/* Bottom Action Area */}
      <div style={{ marginTop: "2rem", display: "flex", justifyContent: "flex-start" }}>
        <Link
          href="/"
          id="btn-privacy-back-bottom"
          className="submit-btn"
          style={{
            maxWidth: "260px",
            textDecoration: "none",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "0.5rem",
          }}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="19" y1="12" x2="5" y2="12" />
            <polyline points="12 19 5 12 12 5" />
          </svg>
          <span>Return to Valuation App</span>
        </Link>
      </div>
    </div>
  );
}
