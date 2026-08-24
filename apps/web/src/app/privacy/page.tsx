import React from "react";

export default function PrivacyPage() {
  return (
    <div style={{ maxWidth: "800px", margin: "0 auto", padding: "1rem 0" }}>
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
    </div>
  );
}
