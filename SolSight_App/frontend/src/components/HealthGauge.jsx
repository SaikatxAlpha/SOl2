import React, { useId } from "react";

const STATUS = {
  Healthy: { color: "var(--ok)", label: "Healthy" },
  Warning: { color: "var(--warn)", label: "Warning" },
  Critical: { color: "var(--bad)", label: "Critical" },
};

/**
 * The "horizon dial" — SolSight's instrument for a single number: panel
 * health. Modeled on a sun crossing a horizon line rather than a generic
 * circular donut. A gradient track runs cyan (thermal-cool / no defect
 * risk) through amber to red as it approaches the danger end; a marker
 * sits at the current reading, and the score itself is set in the
 * display serif, like a number stamped on a physical gauge face.
 */
export default function HealthGauge({ score = 0, status = "Healthy", size = 168, compact = false }) {
  const uid = useId();
  const clamped = Math.max(0, Math.min(100, score));
  const meta = STATUS[status] || { color: "var(--ink-mid)", label: status || "Unknown" };

  const width = size;
  const height = compact ? size * 0.52 : size * 0.62;
  const trackY = height * 0.62;
  const trackX0 = 10;
  const trackX1 = width - 10;
  const trackW = trackX1 - trackX0;
  const markerX = trackX0 + trackW * (clamped / 100);

  const ticks = [0, 25, 50, 75, 100];

  return (
    <div
      style={{ width, display: "flex", flexDirection: "column", alignItems: "center", gap: compact ? 2 : 6 }}
      role="img"
      aria-label={`Health score ${Math.round(clamped)} percent, status ${meta.label}`}
    >
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        <defs>
          {/* userSpaceOnUse: a horizontal line has a zero-height bounding box,
              so the default objectBoundingBox gradient wouldn't paint at all */}
          <linearGradient id={`grad-${uid}`} gradientUnits="userSpaceOnUse" x1={trackX0} y1="0" x2={trackX1} y2="0">
            <stop offset="0%" stopColor="var(--bad)" />
            <stop offset="45%" stopColor="var(--warn)" />
            <stop offset="100%" stopColor="var(--ok)" />
          </linearGradient>
          <filter id={`glow-${uid}`} x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur stdDeviation="3.2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* tick marks */}
        {ticks.map((t) => {
          const x = trackX0 + trackW * (t / 100);
          return (
            <line
              key={t}
              x1={x}
              y1={trackY - 7}
              x2={x}
              y2={trackY - 2}
              stroke="var(--hairline)"
              strokeWidth="1.5"
            />
          );
        })}

        {/* base track */}
        <line
          x1={trackX0}
          y1={trackY}
          x2={trackX1}
          y2={trackY}
          stroke="var(--hairline)"
          strokeWidth="3"
          strokeLinecap="round"
        />

        {/* filled arc-less horizon track, gradient, clipped to score */}
        <line
          x1={trackX0}
          y1={trackY}
          x2={markerX}
          y2={trackY}
          stroke={`url(#grad-${uid})`}
          strokeWidth="3"
          strokeLinecap="round"
        />

        {/* marker: the "sun" */}
        <circle
          cx={markerX}
          cy={trackY}
          r={compact ? 5 : 6.5}
          fill={meta.color}
          filter={`url(#glow-${uid})`}
        />
        <circle cx={markerX} cy={trackY} r={compact ? 2 : 2.5} fill="var(--void)" />
      </svg>

      <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
        <span
          className="numeral"
          style={{ fontSize: compact ? size * 0.24 : size * 0.3, lineHeight: 1, color: "var(--ink)" }}
        >
          {Math.round(clamped)}
        </span>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink-dim)" }}>%</span>
      </div>

      <span
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 11,
          letterSpacing: "0.08em",
          color: meta.color,
          textTransform: "uppercase",
        }}
      >
        {meta.label}
      </span>
    </div>
  );
}
