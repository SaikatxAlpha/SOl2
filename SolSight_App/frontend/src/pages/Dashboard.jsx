import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listPanels, createPanel, clearToken, me } from "../../api/client.js";
import PanelCard from "../components/PanelCard.jsx";
import NavBar from "../components/NavBar.jsx";
import Modal from "../components/Modal.jsx";

export default function Dashboard() {
  const [panels, setPanels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [user, setUser] = useState(null);
  const navigate = useNavigate();

  async function refresh() {
    try {
      const data = await listPanels();
      setPanels(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    me().then(setUser).catch(() => {});
  }, []);

  function handleLogout() {
    clearToken();
    navigate("/login");
  }

  const summary = summarize(panels);

  return (
    <div className="app-shell">
      <NavBar user={user} onLogout={handleLogout} />

      <div className="container" style={{ padding: "36px 24px 64px" }}>
        <header style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 30, gap: 16, flexWrap: "wrap" }}>
          <div>
            <div className="eyebrow" style={{ marginBottom: 8 }}>Fleet overview</div>
            <h1 className="h-display" style={{ fontSize: 32, margin: 0 }}>
              Your panels, at a glance.
            </h1>
          </div>
          <button className="btn btn-solid" onClick={() => setShowForm(true)}>
            + Add panel
          </button>
        </header>

        <div className="grid-stats" style={{ marginBottom: 28 }}>
          <StatCard label="Panels tracked" value={panels.length} accent="cyan" />
          <StatCard label="Needs attention" value={summary.warningOrCritical} accent="amber" />
          <StatCard label="Critical" value={summary.critical} accent="bad" />
        </div>

        {loading && <div className="empty-state h-mono" style={{ padding: "40px 0", color: "var(--ink-dim)" }}>loading fleet…</div>}
        {error && <div className="field-error" style={{ marginBottom: 20 }}>{error}</div>}

        {!loading && panels.length === 0 && (
          <div className="card empty-state">
            <div className="h-display" style={{ fontSize: 20, marginBottom: 8 }}>No panels yet</div>
            <p style={{ fontSize: 14, marginBottom: 18 }}>Add your first panel to start tracking its health.</p>
            <button className="btn btn-solid" onClick={() => setShowForm(true)}>
              + Add panel
            </button>
          </div>
        )}

        <div className="grid-panels">
          {panels.map((p) => (
            <PanelCard key={p.id} panel={p} />
          ))}
        </div>
      </div>

      {showForm && (
        <Modal title="Add a panel" eyebrow="New asset" onClose={() => setShowForm(false)}>
          <AddPanelForm
            onCreated={() => {
              setShowForm(false);
              refresh();
            }}
            onCancel={() => setShowForm(false)}
          />
        </Modal>
      )}
    </div>
  );
}

function summarize(panels) {
  const warningOrCritical = panels.filter((p) => p.latest_status === "Warning" || p.latest_status === "Critical").length;
  const critical = panels.filter((p) => p.latest_status === "Critical").length;
  return { warningOrCritical, critical };
}

function StatCard({ label, value, accent }) {
  const color = accent === "amber" ? "var(--amber)" : accent === "bad" ? "var(--bad)" : "var(--cyan)";
  return (
    <div className="card stat" style={{ borderLeft: `2px solid ${color}` }}>
      <div className="eyebrow">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}

function AddPanelForm({ onCreated, onCancel }) {
  const [panelId, setPanelId] = useState("");
  const [location, setLocation] = useState("");
  const [installDate, setInstallDate] = useState("");
  const [ratedPower, setRatedPower] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await createPanel({
        panel_id: panelId,
        location,
        installation_date: installDate,
        rated_power: parseFloat(ratedPower),
      });
      onCreated();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div className="field">
        <label className="field-label">Panel ID</label>
        <input className="field-input" required value={panelId} onChange={(e) => setPanelId(e.target.value)} placeholder="PNL-014" />
      </div>
      <div className="field">
        <label className="field-label">Location</label>
        <input className="field-input" required value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Rooftop A" />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <div className="field">
          <label className="field-label">Installed</label>
          <input className="field-input" type="date" required value={installDate} onChange={(e) => setInstallDate(e.target.value)} />
        </div>
        <div className="field">
          <label className="field-label">Rated power (W)</label>
          <input className="field-input" type="number" required value={ratedPower} onChange={(e) => setRatedPower(e.target.value)} placeholder="400" />
        </div>
      </div>
      {error && <div className="field-error">{error}</div>}
      <div style={{ display: "flex", gap: 10, marginTop: 4 }}>
        <button type="submit" className="btn btn-solid" style={{ flex: 1 }} disabled={loading}>
          {loading ? "Adding…" : "Add panel"}
        </button>
        <button type="button" className="btn btn-line" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
