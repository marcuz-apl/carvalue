import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import DisclaimerModal from "../components/DisclaimerModal";
import PrivacyModal from "../components/PrivacyModal";
import SiteFooter from "../components/SiteFooter";
import { getAppVersion } from "../lib/version";

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
  const appVersion = getAppVersion();

  return (
    <html lang="en">
      <body className="min-h-full flex flex-col">
        <div className="app-container">
          {/* Main Top Header: Aligned with Main Workspace and Footer (max-width: 1200px) */}
          <header className="site-header">
            <nav className="nav-container" aria-label="Main Navigation">
              {/* Left Column: Docs Link */}
              <div style={{ flex: "1 1 0%", display: "flex", justifyContent: "flex-start", alignItems: "center" }}>
                <Link
                  href="/docs"
                  className="nav-link hover-accent"
                  id="nav-link-docs"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "0.45rem",
                    textDecoration: "none",
                    color: "var(--text-primary)",
                    fontWeight: 600,
                    fontSize: "0.88rem",
                  }}
                >
                  <svg
                    width="17"
                    height="17"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    style={{ color: "var(--accent-primary)" }}
                  >
                    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                  </svg>
                  <span>Docs</span>
                </Link>
              </div>

              {/* Center Column: Product Icon, Name, Subtitle, and Version */}
              <div style={{ flex: "2 1 0%", display: "flex", justifyContent: "center", alignItems: "center" }}>
                <Link
                  href="/"
                  className="brand-logo"
                  id="nav-brand-logo"
                  style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: "0.6rem" }}
                >
                  <svg
                    width="26"
                    height="26"
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
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", lineHeight: 1 }}>
                    <span style={{ fontWeight: 800, fontSize: "1.15rem", letterSpacing: "-0.01em" }}>
                      CarValue™
                    </span>
                    <span style={{ fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--text-muted)", marginTop: "3px" }}>
                      Alberta Vehicle Intelligence
                    </span>
                  </div>
                  <span className="brand-badge" style={{ marginLeft: "0.2rem" }}>
                    {appVersion}
                  </span>
                </Link>
              </div>

              {/* Right Column: Admin Link */}
              <div style={{ flex: "1 1 0%", display: "flex", justifyContent: "flex-end", alignItems: "center" }}>
                <Link
                  href="/admin"
                  className="nav-link"
                  id="nav-link-admin"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "0.4rem",
                    padding: "0.4rem 0.8rem",
                    borderRadius: "0.5rem",
                    background: "rgba(56, 189, 248, 0.08)",
                    border: "1px solid rgba(56, 189, 248, 0.2)",
                    color: "var(--accent-primary)",
                    fontWeight: 600,
                    fontSize: "0.85rem",
                    textDecoration: "none",
                  }}
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
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  </svg>
                  <span>Admin</span>
                </Link>
              </div>
            </nav>
          </header>

          {/* Main App Content Area */}
          <main className="main-content">{children}</main>

          {/* Footer Section mimicking resologix.alfazen.org with popup trigger */}
          <SiteFooter />

          {/* Special Legal & Privacy Popup Window Modals (Global) */}
          <DisclaimerModal />
          <PrivacyModal />
        </div>
      </body>
    </html>
  );
}
