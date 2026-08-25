"use client";

import React, { useEffect, useState } from "react";

interface PrivacyModalProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export default function PrivacyModal({
  isOpen: controlledIsOpen,
  onClose: controlledOnClose,
}: PrivacyModalProps) {
  const [internalIsOpen, setInternalIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const isControlled = controlledIsOpen !== undefined;
  const isOpen = isControlled ? controlledIsOpen : internalIsOpen;

  const handleClose = () => {
    if (isControlled && controlledOnClose) {
      controlledOnClose();
    } else {
      setInternalIsOpen(false);
    }
  };

  useEffect(() => {
    const handleOpenEvent = () => {
      setInternalIsOpen(true);
    };

    window.addEventListener("open-privacy-modal", handleOpenEvent);
    return () => {
      window.removeEventListener("open-privacy-modal", handleOpenEvent);
    };
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        handleClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  // Lock body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  const handleCopy = () => {
    const text = `CARVALUE ALBERTA — DATA RIGHTS & PRIVACY POLICY\n\n1. ZERO PERSONAL DATA COLLECTED: You are never required to enter your name, email, phone number, location GPS, or VIN. Valuations are 100% accessible anonymously.\n\n2. DENY-BY-DEFAULT DATA ACQUISITION: Automated collection strictly uses authorized, licensed sources. We never collect private seller contact details or photos.\n\n3. PRIVACY-MINIMIZED TELEMETRY: We capture only coarse aggregate metrics (response latency, vehicle configuration) with zero persistent visitor fingerprinting or IP tracking.\n\n4. STATUTORY COMPLIANCE: Operates strictly under Alberta PIPA and Canadian PIPEDA standards.`;
    navigator.clipboard?.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  if (!isOpen) return null;

  return (
    <div
      className="disclaimer-modal-overlay"
      onClick={handleClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="privacy-modal-title"
    >
      <div
        className="disclaimer-modal-window privacy-modal-window"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Header Bar */}
        <div className="disclaimer-modal-header privacy-modal-header">
          <div className="disclaimer-title-area">
            <div className="disclaimer-badge privacy-badge">
              <span className="privacy-badge-dot"></span>
              <span>DATA ETHICS • ALBERTA PIPA & CANADIAN PIPEDA</span>
            </div>
            <h2 id="privacy-modal-title" className="disclaimer-heading">
              <svg
                width="22"
                height="22"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                style={{ color: "var(--accent-primary)", flexShrink: 0 }}
              >
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
              <span>Data Rights & Privacy Policy</span>
            </h2>
            <p className="disclaimer-subheading">
              Transparent, Zero-Tracking Privacy Guarantees for Alberta Vehicle Valuation Consumers
            </p>
          </div>

          <button
            type="button"
            className="disclaimer-close-btn"
            onClick={handleClose}
            aria-label="Close data privacy popup window"
            title="Close (Esc)"
          >
            ✕
          </button>
        </div>

        {/* Scrollable Content Body */}
        <div className="disclaimer-modal-body">
          {/* Highlight Callout Box */}
          <div className="privacy-highlight-card">
            <div className="highlight-icon">🛡️</div>
            <div className="highlight-text">
              <strong>Zero-Identity Guarantee:</strong> CarValue will never require an account, phone number, email address, or VIN to calculate asking-price estimates. Your valuations are 100% anonymous and private.
            </div>
          </div>

          {/* Section 1: Zero Personal Data */}
          <div className="disclaimer-clause">
            <div className="clause-header">
              <span className="clause-num">1</span>
              <h3>Zero Personal Data Collected for Valuations</h3>
            </div>
            <p>
              Under Alberta’s <em>Personal Information Protection Act</em> (PIPA) and the federal <em>Personal Information Protection and Electronic Documents Act</em> (PIPEDA), we operate strictly on vehicle attributes:
            </p>
            <ul>
              <li>
                <strong>No User Identity:</strong> We do not ask for or store names, physical addresses, email addresses, or phone numbers.
              </li>
              <li>
                <strong>No VIN Requirement:</strong> Unlike trade-in lead generation sites, we do not require your Vehicle Identification Number (VIN).
              </li>
              <li>
                <strong>No Ad Retargeting:</strong> We do not sell search histories to third-party dealerships or ad brokers.
              </li>
            </ul>
          </div>

          {/* Section 2: Deny-by-Default Data Acquisition */}
          <div className="disclaimer-clause">
            <div className="clause-header">
              <span className="clause-num">2</span>
              <h3>Deny-by-Default Data Acquisition Policy</h3>
            </div>
            <p>
              CarValue applies a strict data rights framework to all market ingestion pipelines:
            </p>
            <ul>
              <li>
                <strong>Permitted Sources Only:</strong> Market listing data is sourced exclusively from permitted dealer feeds and authorized public datasets.
              </li>
              <li>
                <strong>Respect for Bot Controls:</strong> We never bypass logins, paywalls, CAPTCHAs, or <code>robots.txt</code> directives.
              </li>
              <li>
                <strong>Zero Personal Seller Content:</strong> We strictly strip and discard seller names, phone numbers, free-text remarks, and photos during ingestion.
              </li>
            </ul>
          </div>

          {/* Section 3: Privacy-Minimized Telemetry */}
          <div className="disclaimer-clause">
            <div className="clause-header">
              <span className="clause-num">3</span>
              <h3>Privacy-Minimized Coarse Telemetry</h3>
            </div>
            <p>
              To maintain system reliability and valuation accuracy, only minimal, anonymized operational metrics are collected:
            </p>
            <ul>
              <li>
                <strong>Aggregated Diagnostics:</strong> Request execution time, algorithm version used, and coarse vehicle category (e.g. Ford F-150 / 2022).
              </li>
              <li>
                <strong>No IP Storage:</strong> Visitor IP addresses are not stored or associated with valuation records.
              </li>
              <li>
                <strong>No Cross-Site Tracking:</strong> No third-party analytics scripts, tracking pixels, or fingerprinting cookies.
              </li>
            </ul>
          </div>

          {/* Section 4: Automated Retention & Purge */}
          <div className="disclaimer-clause">
            <div className="clause-header">
              <span className="clause-num">4</span>
              <h3>Data Lifecycle & Automatic Purge Schedule</h3>
            </div>
            <p>
              We maintain disciplined retention limits for all operational data:
            </p>
            <ul>
              <li>
                <strong>Observation Retention:</strong> Raw crawl observations exceeding 90 days are automatically purged via scheduled retention jobs.
              </li>
              <li>
                <strong>Admin Security Sessions:</strong> Administrative session tokens expire within 12 hours and are permanently purged after 30 days.
              </li>
            </ul>
          </div>
        </div>

        {/* Modal Window Footer Actions */}
        <div className="disclaimer-modal-footer">
          <div className="footer-meta">
            <span>Statutory Reference: Alberta PIPA / Can. PIPEDA</span>
            <span className="meta-sep">•</span>
            <span>Policy Status: Active (2026.1)</span>
          </div>

          <div className="disclaimer-footer-actions">
            <button
              type="button"
              className="disclaimer-secondary-btn"
              onClick={handleCopy}
              title="Copy privacy policy to clipboard"
            >
              {copied ? "✓ Copied to Clipboard" : "📋 Copy Policy"}
            </button>

            <button
              type="button"
              className="disclaimer-primary-btn privacy-primary-btn"
              onClick={handleClose}
              id="btn-ack-privacy"
            >
              Close & Return to App
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Utility helper to trigger the Privacy modal popup from anywhere in the application.
 */
export function openPrivacyPopup() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("open-privacy-modal"));
  }
}
