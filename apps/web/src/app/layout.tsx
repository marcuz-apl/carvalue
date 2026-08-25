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
      <body className="min-h-full flex flex-col">
        <div className="app-container">
          {/* Main Top Header: Edge-to-Edge with Left Docs, Center Brand, Right Admin */}
          <header className="site-header" style={{ width: "100%" }}>
            <nav
              className="nav-container"
              aria-label="Main Navigation"
              style={{
                width: "100%",
                maxWidth: "100%",
                padding: "0.85rem 1.5rem",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
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
                    v1.2.5
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

          {/* Footer Section mimicking resologix.alfazen.org */}
          <footer
            style={{
              width: "100%",
              fontSize: "0.75rem",
              color: "var(--text-muted)",
              background: "transparent",
              padding: "1.25rem 1.5rem",
              marginTop: "auto",
              borderTop: "1px solid rgba(255, 255, 255, 0.08)",
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "1rem",
            }}
          >
            {/* Left Column: Disclaimer & Privacy Links */}
            <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
              <Link
                href="/docs#disclaimer"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.3rem",
                  color: "var(--text-muted)",
                  transition: "color 0.2s ease",
                  textDecoration: "none",
                }}
                className="hover-accent"
              >
                <svg
                  width="13"
                  height="13"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  style={{ color: "var(--accent-primary)" }}
                >
                  <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" />
                  <path d="M12 8v4" />
                  <path d="M12 16h.01" />
                </svg>
                <span>Disclaimer</span>
              </Link>

              <span style={{ opacity: 0.35 }}>|</span>

              <Link
                href="/privacy"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.3rem",
                  color: "var(--text-muted)",
                  transition: "color 0.2s ease",
                  textDecoration: "none",
                }}
                className="hover-accent"
              >
                <span>Data Rights & Privacy</span>
              </Link>
            </div>

            {/* Center Column: Copyright & System Identity */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.6rem",
                textAlign: "center",
                color: "var(--text-secondary)",
              }}
            >
              <span style={{ fontWeight: 600 }}>CarValue™ Vehicle Intelligence</span>
              <span style={{ opacity: 0.35 }}>|</span>
              <span>© 2026 Alfazen Inc. All rights reserved</span>
            </div>

            {/* Right Column: Social & Contact Links */}
            <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
              <a
                href="mailto:info@alfazen.org"
                style={{ color: "var(--text-muted)", transition: "color 0.2s ease" }}
                title="Get in Touch"
                className="hover-accent"
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
                  <path d="m22 7-8.991 5.727a2 2 0 0 1-2.009 0L2 7" />
                  <rect x="2" y="4" width="20" height="16" rx="2" />
                </svg>
              </a>

              <a
                href="https://alfazen.org"
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: "var(--text-muted)", transition: "color 0.2s ease" }}
                title="Alfazen Homepage"
                className="hover-accent"
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
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
                  <path d="M2 12h20" />
                </svg>
              </a>

              <a
                href="https://x.com/marcuszou"
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: "var(--text-muted)", transition: "color 0.2s ease" }}
                title="X / Twitter"
                className="hover-accent"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                </svg>
              </a>

              <a
                href="https://www.linkedin.com/in/marcuszou/"
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: "var(--text-muted)", transition: "color 0.2s ease" }}
                title="LinkedIn"
                className="hover-accent"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
                </svg>
              </a>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
