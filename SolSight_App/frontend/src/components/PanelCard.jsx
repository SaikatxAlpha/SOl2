import React from "react";
import { useNavigate } from "react-router-dom";
import HealthGauge from "./HealthGauge.jsx";

const STATUS_CLASS = {
  Healthy: "badge-healthy",
  Warning: "badge-warning",
  Critical: "badge-critical",
};

export default function PanelCard({ panel }) {
  const navigate = useNavigate();
  const hasData = panel.latest_health_score != null;
  const go = () => navigate(`/panels/${panel.panel_id}`);

  return (
    <div
      className={`card card-interactive${panel.latest_status ? ` card-accent-${panel.latest_status === "Healthy" ? "cyan" : "amber"}` : ""}`}
      onClick={go}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && go()}
      style={{ padding: 20, display: "flex", flexDirection: "column", gap: 16 }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 10 }}>
        <div style={{ minWidth: 0 }}>
          <div className="eyebrow">{panel.location}</div>
          <div
            className="h-mono"
            style={{ fontSize: 18, marginTop: 6, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
          >
            {panel.panel_id}
          </div>
          <div style={{ fontSize: 12, color: "var(--ink-dim)", fontFamily: "var(--font-mono)", marginTop: 4 }}>
            {panel.rated_power}W rated
          </div>
        </div>
        {panel.latest_status && (
          <span className={`badge ${STATUS_CLASS[panel.latest_status] || ""}`}>
            <span className="badge-dot" />
            {panel.latest_status}
          </span>
        )}
      </div>

      <div style={{ display: "flex", justifyContent: "center", padding: "2px 0 4px" }}>
        {hasData ? (
          <HealthGauge score={panel.latest_health_score} status={panel.latest_status} size={140} />
        ) : (
          <div
            style={{
              width: "100%",
              padding: "22px 12px",
              borderRadius: "var(--r-sm)",
              border: "1px dashed var(--hairline)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--ink-dim)",
              fontFamily: "var(--font-mono)",
              fontSize: 12,
              textAlign: "center",
            }}
          >
            awaiting first inspection
          </div>
        )}
      </div>
    </div>
  );
}
