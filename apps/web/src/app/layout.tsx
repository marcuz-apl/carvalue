import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "CarValue Alberta | Explainable Used Pickup Asking-Price Valuator",
  description:
    "Evidence-based, transparent asking-price estimates for used pickup trucks in Alberta, Canada. 80% prediction intervals, freshness metrics, zero tracking.",
  openGraph: {
    title: "CarValue Alberta — Used Pickup Asking-Price Valuator",
    description:
      "Explainable used-pickup asking price valuations with prediction intervals and market evidence for Alberta, Canada.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="app-container">
          <header className="site-header">
            <nav className="nav-container" aria-label="Main Navigation">
              <Link href="/" className="brand-logo" id="nav-brand-logo">
                <svg
                  width="28"
                  height="28"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  style={{ color: "var(--accent-primary)" }}
                >
                  <path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.4 2.9A3.7 3.7 0 0 0 2 12v4c0 .6.4 1 1 1h2" />
                  <circle cx="7" cy="17" r="2" />
                  <path d="M9 17h6" />
                  <circle cx="17" cy="17" r="2" />
                </svg>
                <span>CarValue</span>
                <span className="brand-badge">Alberta MVP</span>
              </Link>

              <div className="nav-links">
                <Link href="/" className="nav-link" id="nav-link-calculator">
                  Valuator
                </Link>
                <Link href="/methodology" className="nav-link" id="nav-link-methodology">
                  Methodology
                </Link>
                <Link href="/privacy" className="nav-link" id="nav-link-privacy">
                  Privacy
                </Link>
              </div>
            </nav>
          </header>

          <main className="main-content">{children}</main>

          <footer className="site-footer">
            <div className="footer-content">
              <div>
                <p>
                  <strong>CarValue Alberta</strong> — Explainable Used Pickup Valuator.
                </p>
                <p style={{ marginTop: "0.25rem", fontSize: "0.8rem" }}>
                  All prices in Canadian Dollars (CAD). Kilometres standard.
                </p>
              </div>

              <div className="footer-links">
                <Link href="/methodology" className="footer-link">
                  Model Governance
                </Link>
                <Link href="/privacy" className="footer-link">
                  Data Rights & Privacy
                </Link>
              </div>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
