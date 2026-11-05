import React from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from "recharts";

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const point = payload[0];
  const isProjected = point.dataKey === "projected";
  return (
    <div
      style={{
        background: "var(--surface-2)",
        border: "1px solid var(--hairline)",
        borderRadius: 10,
        padding: "9px 13px",
        fontFamily: "var(--font-mono)",
        fontSize: 12,
        boxShadow: "var(--shadow-pop)",
      }}
    >
      <div style={{ color: "var(--ink-dim)", marginBottom: 2 }}>{label}</div>
      <div style={{ color: isProjected ? "var(--cyan)" : "var(--amber)", fontWeight: 600 }}>
        {point.value}% {isProjected ? "projected" : "recorded"}
      </div>
    </div>
  );
}

/**
 * history: [{ date, health_score }]
 * forecast: [{ day, predicted_health }]  (day = +N from today, e.g. 30/60/90)
 */
export default function DegradationChart({ history = [], forecast = [] }) {
  const historyPoints = history.map((h) => ({
    label: new Date(h.date).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    actual: h.health_score,
  }));

  const forecastPoints = forecast.map((f) => ({
    label: `+${f.day}d`,
    projected: f.predicted_health,
  }));

  // The forecast line starts from the last recorded point, so give that
  // point a projected value too (instead of a duplicate "today" entry).
  const last = historyPoints[historyPoints.length - 1];
  if (last) last.projected = last.actual;

  const data = [...historyPoints, ...forecastPoints];
  const todayLabel = last?.label;

  return (
    <div style={{ width: "100%", height: 220 }}>
      <ResponsiveContainer>
        <AreaChart data={data} margin={{ top: 8, right: 12, left: -6, bottom: 0 }}>
          <defs>
            <linearGradient id="actualFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--amber)" stopOpacity={0.35} />
              <stop offset="100%" stopColor="var(--amber)" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="projectedFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--cyan)" stopOpacity={0.28} />
              <stop offset="100%" stopColor="var(--cyan)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="var(--hairline-soft)" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fill: "var(--ink-dim)", fontSize: 11, fontFamily: "var(--font-mono)" }}
            axisLine={{ stroke: "var(--hairline)" }}
            tickLine={false}
            interval="preserveStartEnd"
            minTickGap={18}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fill: "var(--ink-dim)", fontSize: 11, fontFamily: "var(--font-mono)" }}
            axisLine={false}
            tickLine={false}
            width={34}
          />
          {todayLabel && (
            <ReferenceLine x={todayLabel} stroke="var(--hairline)" strokeDasharray="3 3" />
          )}
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="actual"
            stroke="var(--amber)"
            strokeWidth={2}
            fill="url(#actualFill)"
            connectNulls
          />
          <Area
            type="monotone"
            dataKey="projected"
            stroke="var(--cyan)"
            strokeWidth={2}
            strokeDasharray="5 4"
            fill="url(#projectedFill)"
            connectNulls
          />
        </AreaChart>
      </ResponsiveContainer>
      <div style={{ display: "flex", gap: 16, marginTop: 6, justifyContent: "center" }}>
        <Legend swatch="var(--amber)" label="Recorded" />
        <Legend swatch="var(--cyan)" label="Forecast" dashed />
      </div>
    </div>
  );
}

function Legend({ swatch, label, dashed }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <span
        style={{
          width: 14,
          height: 2,
          background: dashed
            ? `repeating-linear-gradient(90deg, ${swatch} 0 4px, transparent 4px 7px)`
            : swatch,
          display: "inline-block",
        }}
      />
      <span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--ink-dim)" }}>
        {label}
      </span>
    </div>
  );
}
