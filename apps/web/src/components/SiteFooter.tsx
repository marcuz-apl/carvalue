"use client";

import Link from "next/link";
import React from "react";
import { openDisclaimerPopup } from "./DisclaimerModal";
import { openPrivacyPopup } from "./PrivacyModal";

export default function SiteFooter() {
  return (
    <footer className="site-footer-custom" id="site-footer">
      <div className="site-footer-inner">
        {/* Left Part: Symmetrical Centered Disclaimer & Data Privacy Buttons */}
        <div className="footer-col-left">
          <button
            type="button"
            onClick={openDisclaimerPopup}
            id="footer-btn-disclaimer"
            className="footer-pill-btn footer-btn-disclaimer hover-accent"
            title="Open Statutory Consumer Notice & Legal Disclaimer Window"
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
              style={{ color: "#f59e0b" }}
            >
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              <path d="M12 8v4" />
              <path d="M12 16h.01" />
            </svg>
            <span>Disclaimer</span>
          </button>

          <button
            type="button"
            onClick={openPrivacyPopup}
            id="footer-btn-privacy"
            className="footer-pill-btn footer-btn-privacy hover-accent"
            title="Open Data Privacy & Consumer Rights Window"
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
              style={{ color: "var(--accent-primary)" }}
            >
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
            <span>Data Privacy</span>
          </button>
        </div>

        {/* Central Part: Brand & Copyright Details */}
        <div className="footer-col-center">
          <span className="footer-brand-text">CarValue™ Vehicle Intelligence</span>
          <span className="footer-divider">•</span>
          <span className="footer-copyright-text">© 2026 Alfazen Inc. All rights reserved</span>
        </div>

        {/* Right Part: Social & Contact Links */}
        <div className="footer-col-right">
          <a
            href="mailto:info@alfazen.org"
            className="footer-social-icon hover-accent"
            title="Get in Touch"
          >
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="m22 7-8.991 5.727a2 2 0 0 1-2.009 0L2 7" />
              <rect x="2" y="4" width="20" height="16" rx="2" />
            </svg>
          </a>

          <a
            href="https://alfazen.org"
            target="_blank"
            rel="noopener noreferrer"
            className="footer-social-icon hover-accent"
            title="Alfazen Homepage"
          >
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="10" />
              <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
              <path d="M2 12h20" />
            </svg>
          </a>

          <a
            href="https://x.com/marcuszou"
            target="_blank"
            rel="noopener noreferrer"
            className="footer-social-icon hover-accent"
            title="X / Twitter"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
            </svg>
          </a>

          <a
            href="https://www.linkedin.com/in/marcuszou/"
            target="_blank"
            rel="noopener noreferrer"
            className="footer-social-icon hover-accent"
            title="LinkedIn"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
            </svg>
          </a>
        </div>
      </div>
    </footer>
  );
}
