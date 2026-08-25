"use client";

import React, { useEffect, useState } from "react";

interface DisclaimerModalProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export default function DisclaimerModal({ isOpen: controlledIsOpen, onClose: controlledOnClose }: DisclaimerModalProps) {
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
    // Listen for global trigger events
    const handleOpenEvent = () => {
      setInternalIsOpen(true);
    };

    window.addEventListener("open-disclaimer-modal", handleOpenEvent);
    return () => {
      window.removeEventListener("open-disclaimer-modal", handleOpenEvent);
    };
  }, []);

  useEffect(() => {
    // Escape key listener
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
    const text = `CARVALUE ALBERTA — MANDATORY CONSUMER NOTICE & STATUTORY DISCLAIMER\n\n1. NON-APPRAISAL ESTIMATE: CarValue provides empirical, statistical asking-price estimates derived from mathematical regressions on Alberta used pickup market data. It does not constitute a certified appraisal, formal trade-in guarantee, or binding purchase contract.\n\n2. UNCERTAINTY INTERVALS: Every valuation includes an 80% prediction interval. Actual transaction values depend on mechanical condition, maintenance, tire wear, accident claims (AMVIC/Carfax), and dealer negotiations.\n\n3. ALBERTA JURISDICTION: All values are in Canadian Dollars ($ CAD) and metric kilometres (km), conforming to Alberta Consumer Protection Act standards.\n\n4. ZERO TRACKING PRIVACY: No personal identity, email, phone, or VIN is collected or sold.`;
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
      aria-labelledby="disclaimer-modal-title"
    >
      <div
        className="disclaimer-modal-window"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Header Bar */}
        <div className="disclaimer-modal-header">
          <div className="disclaimer-title-area">
            <div className="disclaimer-badge">
              <span className="disclaimer-badge-dot"></span>
              <span>STATUTORY ADVISORY • ALBERTA JURISDICTION</span>
            </div>
            <h2 id="disclaimer-modal-title" className="disclaimer-heading">
              <svg
                width="22"
                height="22"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                style={{ color: "#f59e0b", flexShrink: 0 }}
              >
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                <path d="M12 8v4" />
                <path d="M12 16h.01" />
              </svg>
              <span>Mandatory Consumer Notice & Legal Disclaimer</span>
            </h2>
            <p className="disclaimer-subheading">
              Official Valuation Disclosures & Regulatory Guidance for Alberta Used Vehicle Consumers
            </p>
          </div>

          <button
            type="button"
            className="disclaimer-close-btn"
            onClick={handleClose}
            aria-label="Close disclaimer popup window"
            title="Close (Esc)"
          >
            ✕
          </button>
        </div>

        {/* Scrollable Content Body */}
        <div className="disclaimer-modal-body">
          {/* Highlight Callout Box */}
          <div className="disclaimer-highlight-card">
            <div className="highlight-icon">⚠️</div>
            <div className="highlight-text">
              <strong>Important Consumer Warning:</strong> Asking prices represent listing offers in the marketplace, not final closed sales. This valuation is a statistical calculation and must never be treated as a legally binding offer or certified appraisal.
            </div>
          </div>

          {/* Section 1: Non-Appraisal & Non-Binding Advisory */}
          <div className="disclaimer-clause">
            <div className="clause-header">
              <span className="clause-num">1</span>
              <h3>Asking-Price Estimation vs. Certified Appraisal</h3>
            </div>
            <p>
              The figures displayed across the CarValue platform represent <strong>asking-price statistical estimates</strong> generated via statistical regression models (OLS baseline and CatBoost algorithms) trained on empirical Alberta dealer and marketplace listing records.
            </p>
            <ul>
              <li>
                <strong>Not a Professional Appraisal:</strong> This tool is not a substitute for an inspection by an AMVIC-licensed automotive technician or certified appraiser.
              </li>
              <li>
                <strong>No Guaranteed Purchase / Trade-In:</strong> Neither CarValue nor any affiliated entity guarantees that any dealership or private buyer will transact at or near this estimated figure.
              </li>
            </ul>
          </div>

          {/* Section 2: Uncertainty Bands & Prediction Intervals */}
          <div className="disclaimer-clause">
            <div className="clause-header">
              <span className="clause-num">2</span>
              <h3>Statistical Uncertainty & 80% Prediction Intervals</h3>
            </div>
            <p>
              Vehicle pricing exhibits natural dispersion. Each valuation is accompanied by an <strong>80% prediction interval</strong> bounding the expected asking price:
            </p>
            <ul>
              <li>
                <strong>Condition Variance:</strong> Paint quality, interior wear, rust (especially from Alberta road salt and gravel), and mechanical soundness strongly influence transaction prices.
              </li>
              <li>
                <strong>Vehicle History:</strong> Open recalls, Carfax accident claim histories, active status vs. rebuilt/salvage titles, and maintenance records will cause substantial variation from the baseline estimate.
              </li>
              <li>
                <strong>Dealer Reconditioning & Warranty:</strong> Dealer asking prices frequently reflect safety inspections, reconditioning costs, and warranty inclusions that differ from private party sales.
              </li>
            </ul>
          </div>

          {/* Section 3: Alberta Jurisdiction & Currency Standards */}
          <div className="disclaimer-clause">
            <div className="clause-header">
              <span className="clause-num">3</span>
              <h3>Alberta Jurisdiction & Measurement Standards</h3>
            </div>
            <p>
              In compliance with Alberta Consumer Protection legislation and transparent advertising guidelines:
            </p>
            <ul>
              <li>All valuations, intervals, and price histories are strictly expressed in <strong>Canadian Dollars ($ CAD)</strong>.</li>
              <li>All odometer readings are modeled and calculated in <strong>metric kilometres (km)</strong>.</li>
              <li>Market dynamics, supply volumes, and seasonal truck demands reflect the unique geographic reality of <strong>Alberta, Canada</strong>.</li>
            </ul>
          </div>

          {/* Section 4: Privacy & No-VIN Guarantee */}
          <div className="disclaimer-clause">
            <div className="clause-header">
              <span className="clause-num">4</span>
              <h3>Zero-Tracking Consumer Privacy (PIPA Compliance)</h3>
            </div>
            <p>
              Under Alberta’s <em>Personal Information Protection Act</em> (PIPA) and the federal <em>Personal Information Protection and Electronic Documents Act</em> (PIPEDA):
            </p>
            <ul>
              <li>We <strong>do not collect</strong> your name, phone number, email address, IP address, or vehicle VIN to generate valuations.</li>
              <li>Your searches are never monetized, sold to third-party dealerships, or used for behavioral ad retargeting.</li>
            </ul>
          </div>
        </div>

        {/* Modal Window Footer Actions */}
        <div className="disclaimer-modal-footer">
          <div className="footer-meta">
            <span>Statutory Reference: AB Fair Trading Act RSA 2000</span>
            <span className="meta-sep">•</span>
            <span>Version: 2026.1-AB</span>
          </div>

          <div className="disclaimer-footer-actions">
            <button
              type="button"
              className="disclaimer-secondary-btn"
              onClick={handleCopy}
              title="Copy disclaimer text to clipboard"
            >
              {copied ? "✓ Copied to Clipboard" : "📋 Copy Notice"}
            </button>

            <button
              type="button"
              className="disclaimer-primary-btn"
              onClick={handleClose}
              id="btn-ack-disclaimer"
            >
              I Understand & Acknowledge
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Utility helper to trigger the Disclaimer modal popup from anywhere in the application.
 */
export function openDisclaimerPopup() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("open-disclaimer-modal"));
  }
}
