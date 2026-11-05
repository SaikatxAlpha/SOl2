import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login, register, setToken } from "../../api/client.js";

export default function Login() {
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = mode === "login" ? await login(email, password) : await register(name, email, password);
      setToken(res.access_token);
      navigate("/");
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "grid", gridTemplateColumns: "1.1fr 1fr" }} className="login-grid">
      {/* ---- signature side: the instrument hero ---- */}
      <div
        style={{
          position: "relative",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "44px 48px",
          background:
            "radial-gradient(ellipse 700px 500px at 20% 10%, rgba(255,157,61,0.12), transparent 60%), radial-gradient(ellipse 600px 500px at 90% 90%, rgba(79,227,201,0.09), transparent 55%), var(--surface)",
          borderRight: "1px solid var(--hairline-soft)",
        }}
        className="login-hero"
      >
        <Wordmark />

        <div>
          <div className="eyebrow" style={{ marginBottom: 14 }}>Fleet instrument · live read</div>
          <h1 className="h-display" style={{ fontSize: 40, lineHeight: 1.12, maxWidth: 460, margin: 0 }}>
            Every panel reports its own condition.
          </h1>
          <p style={{ maxWidth: 420, marginTop: 16, fontSize: 15 }}>
            CNN defect scans, health classification, and 90-day degradation
            forecasts — run per panel, logged per inspection.
          </p>
          <ReadoutStrip />
        </div>

        <div style={{ fontFamily: "var(--font-mono)", fontSize: 11.5, color: "var(--ink-dim)" }}>
          © {new Date().getFullYear()} SolSight · panel intel, not paperwork
        </div>
      </div>

      {/* ---- form side ---- */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
        <div style={{ width: "100%", maxWidth: 380 }}>
          <div style={{ marginBottom: 26 }}>
            <div className="eyebrow" style={{ marginBottom: 8 }}>
              {mode === "login" ? "Welcome back" : "Get set up"}
            </div>
            <h2 className="h-display" style={{ fontSize: 26, margin: 0 }}>
              {mode === "login" ? "Sign in to your fleet" : "Create your account"}
            </h2>
          </div>

          <form onSubmit={handleSubmit} className="card" style={{ padding: 26, display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ display: "flex", gap: 6, background: "var(--surface-3)", padding: 4, borderRadius: 10 }}>
              <TabButton active={mode === "login"} onClick={() => setMode("login")}>
                Sign in
              </TabButton>
              <TabButton active={mode === "register"} onClick={() => setMode("register")}>
                Create account
              </TabButton>
            </div>

            {mode === "register" && (
              <div className="field">
                <label className="field-label">Name</label>
                <input className="field-input" required value={name} onChange={(e) => setName(e.target.value)} placeholder="Ada Lovelace" />
              </div>
            )}
            <div className="field">
              <label className="field-label">Email</label>
              <input
                className="field-input"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@fleet.io"
              />
            </div>
            <div className="field">
              <label className="field-label">Password</label>
              <input
                className="field-input"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>

            {error && <div className="field-error">{error}</div>}

            <button type="submit" className="btn btn-solid btn-block" disabled={loading} style={{ marginTop: 4, padding: "13px 18px" }}>
              {loading ? "Working…" : mode === "login" ? "Sign in" : "Create account"}
            </button>
          </form>
        </div>
      </div>

      <style>{`
        @media (max-width: 860px) {
          .login-grid { grid-template-columns: 1fr; }
          .login-hero { display: none !important; }
        }
      `}</style>
    </div>
  );
}

function ReadoutStrip() {
  const items = [
    { label: "Defect classes", value: "4" },
    { label: "Forecast horizon", value: "90d" },
    { label: "Model stack", value: "CNN → MLP → BiLSTM" },
  ];
  return (
    <div style={{ display: "flex", gap: 26, marginTop: 30, flexWrap: "wrap" }}>
      {items.map((it) => (
        <div key={it.label}>
          <div className="h-mono" style={{ fontSize: 15, color: "var(--amber)" }}>{it.value}</div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 10.5, color: "var(--ink-dim)", marginTop: 3, textTransform: "uppercase", letterSpacing: "0.06em" }}>
            {it.label}
          </div>
        </div>
      ))}
    </div>
  );
}

function TabButton({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="btn"
      style={{
        flex: 1,
        background: active ? "var(--surface)" : "transparent",
        color: active ? "var(--ink)" : "var(--ink-dim)",
        boxShadow: "none",
        padding: "9px 12px",
      }}
    >
      {children}
    </button>
  );
}

function Wordmark() {
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 10 }}>
      <svg width="30" height="30" viewBox="0 0 30 30" fill="none">
        <circle cx="15" cy="15" r="7" fill="var(--amber)" style={{ filter: "drop-shadow(0 0 6px var(--amber))" }} />
        <g stroke="var(--amber)" strokeWidth="2" strokeLinecap="round" opacity="0.7">
          <line x1="15" y1="1" x2="15" y2="5" />
          <line x1="15" y1="25" x2="15" y2="29" />
          <line x1="1" y1="15" x2="5" y2="15" />
          <line x1="25" y1="15" x2="29" y2="15" />
        </g>
      </svg>
      <span className="h-mono" style={{ fontSize: 17 }}>
        SolSight
      </span>
    </div>
  );
}
