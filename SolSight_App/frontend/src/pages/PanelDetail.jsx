import React, { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getPanel, getPanelHistory, getPanelPrediction, deletePanel, clearToken } from "../../api/client.js";
import HealthGauge from "../components/HealthGauge.jsx";
import DegradationChart from "../components/DegradationChart.jsx";
import UploadForm from "../components/UploadForm.jsx";
import NavBar from "../components/NavBar.jsx";

const STATUS_CLASS = {
  Healthy: "badge-healthy",
  Warning: "badge-warning",
  Critical: "badge-critical",
};

export default function PanelDetail() {
  const { panelId } = useParams();
  const navigate = useNavigate();
  const [panel, setPanel] = useState(null);
  const [history, setHistory] = useState([]);
  const [prediction, setPrediction] = useState(null);
  const [lastResult, setLastResult] = useState(null);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [p, h] = await Promise.all([getPanel(panelId), getPanelHistory(panelId)]);
      setPanel(p);
      setHistory(h);
      try {
        setPrediction(await getPanelPrediction(panelId));
      } catch {
        setPrediction(null);
      }
    } catch (err) {
      setError(err.message);
    }
  }, [panelId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  function handleResult(result) {
    setLastResult(result);
    refresh();
  }

  function handleLogout() {
    clearToken();
    navigate("/login");
  }

  async function handleDelete() {
    if (!window.confirm(`Remove ${panelId} and all of its inspections? This can't be undone.`)) return;
    try {
      await deletePanel(panelId);
      navigate("/");
    } catch (err) {
      setError(err.message);
    }
  }

  if (error) {
    return (
      <div className="app-shell">
        <NavBar onLogout={handleLogout} />
        <div className="container" style={{ padding: "60px 24px" }}>
          <div className="field-error" style={{ marginBottom: 16 }}>{error}</div>
          <button className="btn btn-line" onClick={() => navigate("/")}>
            ← Back to fleet
          </button>
        </div>
      </div>
    );
  }

  if (!panel) {
    return (
      <div className="app-shell">
        <NavBar onLogout={handleLogout} />
        <div style={{ padding: 40, color: "var(--ink-dim)", fontFamily: "var(--font-mono)" }}>loading panel…</div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <NavBar onLogout={handleLogout} />

      <div className="container" style={{ padding: "28px 24px 64px" }}>
        <button className="btn btn-ghost" onClick={() => navigate("/")} style={{ marginBottom: 18, paddingLeft: 0 }}>
          ← Fleet
        </button>

        <header style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 20, marginBottom: 28 }}>
          <div>
            <div className="eyebrow">{panel.location}</div>
            <h1 className="h-display" style={{ fontSize: 30, margin: "8px 0 6px" }}>
              {panel.panel_id}
            </h1>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--ink-dim)" }}>
              {panel.rated_power}W rated · installed {panel.installation_date}
            </div>
          </div>
          {panel.latest_health_score != null && (
            <HealthGauge score={panel.latest_health_score} status={panel.latest_status} size={148} />
          )}
        </header>

        <div className="detail-grid">
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div className="card" style={{ padding: 22 }}>
              <div className="eyebrow" style={{ marginBottom: 14 }}>Degradation forecast</div>
              <DegradationChart history={history} forecast={prediction?.degradation_forecast || []} />
            </div>

            {prediction?.recommendation && (
              <div className="card card-accent-amber" style={{ padding: 20 }}>
                <div className="eyebrow" style={{ marginBottom: 10 }}>Recommendation</div>
                <p style={{ fontSize: 14, color: "var(--ink)", margin: 0, lineHeight: 1.5 }}>
                  {prediction.recommendation}
                </p>
              </div>
            )}

            {lastResult && (
              <div className="card" style={{ padding: 20 }}>
                <div className="eyebrow" style={{ marginBottom: 14 }}>Latest analysis</div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, fontFamily: "var(--font-mono)", fontSize: 13 }}>
                  <Metric label="Detected" value={lastResult.detected_defect} />
                  <Metric label="Confidence" value={`${lastResult.confidence}%`} />
                  <Metric label="Power output" value={`${lastResult.power_output} W`} />
                  <Metric label="Expected at this temp" value={`${lastResult.expected_power} W`} />
                  <Metric label="Power loss" value={`${lastResult.power_loss_pct}%`} />
                  <Metric label="Health score" value={`${lastResult.health_score}%`} />
                </div>
                {lastResult.analysis_mode && (
                  <div style={{ marginTop: 16, fontSize: 11.5, color: "var(--ink-dim)", fontFamily: "var(--font-mono)" }}>
                    defect: {lastResult.analysis_mode.defect} · health: {lastResult.analysis_mode.health} · forecast:{" "}
                    {lastResult.analysis_mode.forecast}
                  </div>
                )}
              </div>
            )}
          </div>

          <UploadForm panelId={panelId} onResult={handleResult} />
        </div>

        <section style={{ marginTop: 32 }}>
          <div className="eyebrow" style={{ marginBottom: 12 }}>Inspection log</div>
          <div className="card" style={{ overflow: "hidden" }}>
            {history.length === 0 ? (
              <div className="empty-state" style={{ fontFamily: "var(--font-mono)", fontSize: 13, padding: 30 }}>
                No inspections recorded yet.
              </div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Health</th>
                      <th>Status</th>
                      <th>Defect</th>
                      <th>Confidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...history].reverse().map((row, i) => (
                      <tr key={i}>
                        <td>{new Date(row.date).toLocaleString()}</td>
                        <td className="h-mono">{row.health_score}</td>
                        <td>
                          <span className={`badge ${STATUS_CLASS[row.status] || ""}`}>
                            <span className="badge-dot" />
                            {row.status}
                          </span>
                        </td>
                        <td>{row.detected_defect}</td>
                        <td>{row.confidence}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>

        <div style={{ marginTop: 28, display: "flex", justifyContent: "flex-end" }}>
          <button className="btn btn-line" onClick={handleDelete} style={{ color: "var(--bad)" }}>
            Remove panel
          </button>
        </div>
      </div>

      <style>{`
        .detail-grid {
          display: grid;
          grid-template-columns: 1.2fr 1fr;
          gap: 20px;
          align-items: start;
        }
        @media (max-width: 820px) {
          .detail-grid { grid-template-columns: 1fr; }
        }
      `}</style>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div>
      <div style={{ color: "var(--ink-dim)", fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.06em" }}>{label}</div>
      <div style={{ color: "var(--ink)", marginTop: 4 }}>{value}</div>
    </div>
  );
}
