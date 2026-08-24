"use client";

import React, { useState } from "react";

export default function AdminPanel() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [token, setToken] = useState("");
  const [message, setMessage] = useState("");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch("/api/admin/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (res.ok) {
        const data = await res.json();
        setIsLoggedIn(true);
        setToken(data.csrf_token);
        setMessage(`Logged in as ${data.email}`);
      } else {
        setMessage("Invalid credentials");
      }
    } catch {
      setMessage("Login failed (API offline or blocked)");
    }
  };

  return (
    <div className="glass-card" style={{ maxWidth: "600px", margin: "2rem auto" }}>
      <h2 style={{ fontSize: "1.25rem", marginBottom: "1rem" }}>Operator Admin Access</h2>
      {!isLoggedIn ? (
        <form onSubmit={handleLogin}>
          <div className="form-group">
            <label className="form-label">Admin Email</label>
            <input
              type="email"
              className="form-control"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@carvalue.ca"
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              type="password"
              className="form-control"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button type="submit" className="submit-btn">
            Sign In to Admin Portal
          </button>
          {message && <p style={{ marginTop: "0.75rem", fontSize: "0.85rem", color: "var(--accent-amber)" }}>{message}</p>}
        </form>
      ) : (
        <div>
          <p style={{ color: "var(--accent-secondary)", marginBottom: "1rem" }}>{message}</p>
          <div style={{ display: "flex", gap: "1rem" }}>
            <button
              type="button"
              className="submit-btn"
              style={{ background: "var(--bg-surface-elevated)", color: "var(--text-primary)" }}
              onClick={() => {
                setIsLoggedIn(false);
                setMessage("");
              }}
            >
              Sign Out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
