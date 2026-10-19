import { useState, useRef } from "react";
import { ErrorState } from "../../errors";
import { useAsync } from "../../hooks/useAsync";
import { sentimentApi } from "../../services/sentimentApi";

const SCOPES = [
  { key: "crypto", label: "Crypto" },
  { key: "nft", label: "NFTs" },
  { key: "realEstate", label: "Real Estate" },
  { key: "both", label: "All" },
];
const RANGES = [
  { key: 7, label: "7d" },
  { key: 30, label: "30d" },
  { key: 90, label: "90d" },
];

const LINE_META = {
  crypto: { label: "Crypto" },
  nft: { label: "NFTs" },
  realEstate: { label: "Real Estate" },
};

const DAY_MS = 86400000;

// Same scale as the mood gauge above it: -100 (all negative) to +100 (all positive).
const MIN = -100;
const MAX = 100;
const Y_TICKS = [-100, -50, 0, 50, 100];
const signed = (n) => `${n > 0 ? "+" : ""}${n}`;

function formatDate(ms) {
  return new Date(ms).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

// Points keyed by their own timestamps; anything without a readable date is dropped rather
// than given an invented position.
function toPoints(series) {
  return (series || [])
    .map((p) => ({ t: new Date(p.date).getTime(), value: p.value }))
    .filter((p) => Number.isFinite(p.t))
    .sort((a, b) => a.t - b.t);
}

function buildPath(points, t0, t1, geo) {
  const { W, H, PAD_L, PAD_R, PAD_T, PAD_B } = geo;
  const plotW = W - PAD_L - PAD_R;
  const plotH = H - PAD_T - PAD_B;
  const span = Math.max(1, t1 - t0);

  const pts = points.map((p) => ({
    x: PAD_L + ((p.t - t0) / span) * plotW,
    y: PAD_T + plotH - ((p.value - MIN) / (MAX - MIN)) * plotH,
    t: p.t,
    value: p.value,
  }));

  const linePath = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
  const baseY = PAD_T + plotH - ((0 - MIN) / (MAX - MIN)) * plotH; // fill toward the zero line
  const areaPath = `${linePath} L ${pts[pts.length - 1].x.toFixed(1)} ${baseY} L ${pts[0].x.toFixed(1)} ${baseY} Z`;
  return { linePath, areaPath, last: pts[pts.length - 1], pts };
}

export default function MoodTrendChart({ colors }) {
  const [scope, setScope] = useState("crypto");
  const [days, setDays] = useState(30);
  const [hover, setHover] = useState(null); // timestamp (ms) of the point being inspected
  const containerRef = useRef(null);

  const { data: series, loading, error, refetch } = useAsync(() => sentimentApi.getMoodTrend(scope, days), [scope, days]);

  const geo = { W: 900, H: 220, PAD_L: 40, PAD_R: 16, PAD_T: 16, PAD_B: 28 };
  const { W, H, PAD_L, PAD_R, PAD_T, PAD_B } = geo;
  const plotW = W - PAD_L - PAD_R;
  const plotH = H - PAD_T - PAD_B;

  const isMulti = scope === "both";

  const lines = isMulti && series && !Array.isArray(series)
    ? series
    : !isMulti && series && Array.isArray(series)
      ? { [scope]: series }
      : {};

  const lineColor = {
    crypto: colors.accent,
    nft: colors.purple,
    realEstate: colors.teal,
  };

  const points = {};
  Object.entries(lines).forEach(([key, values]) => {
    points[key] = toPoints(values);
  });

  // The x axis spans the selected number of days ending at the newest reading, and every
  // point sits at its own timestamp. So a gap in the history shows as a gap, and short
  // history shows as short history instead of being stretched across the whole window.
  const allTimes = Object.values(points).flat().map((p) => p.t);
  const t1 = allTimes.length ? Math.max(...allTimes) : 0;
  const t0 = t1 - days * DAY_MS;

  const lineData = {};
  Object.entries(points).forEach(([key, pts]) => {
    if (pts.length >= 2) lineData[key] = buildPath(pts, t0, t1, geo);
  });

  const xTicks = Object.keys(lineData).length
    ? Array.from({ length: 5 }, (_, c) => {
        const fraction = c / 4;
        return { x: PAD_L + fraction * plotW, label: formatDate(t0 + fraction * (t1 - t0)) };
      })
    : [];

  const handleMouseMove = (e) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const svgX = ((e.clientX - rect.left) / rect.width) * W;
    const t = t0 + ((svgX - PAD_L) / plotW) * (t1 - t0);

    let nearest = null;
    Object.values(lineData).forEach((data) => {
      data.pts.forEach((p) => {
        if (nearest == null || Math.abs(p.t - t) < Math.abs(nearest - t)) nearest = p.t;
      });
    });
    setHover(nearest);
  };

  // Per line, the reading closest to the hovered time — each line's own timestamp is shown.
  const hovered = hover == null ? null : Object.entries(lineData).map(([key, data]) => {
    const pt = data.pts.reduce((best, p) => (Math.abs(p.t - hover) < Math.abs(best.t - hover) ? p : best), data.pts[0]);
    return { key, pt };
  });
  const hoverX = hovered?.length ? hovered[0].pt.x : null;
  const hoverFraction = hoverX != null ? hoverX / W : 0;

  return (
    <div className="sv2-card sv2-card-pad" style={{ position: "relative" }}>
      <div className="sv2-flex-between" style={{ flexWrap: "wrap", gap: 12 }}>
        <span className="sv2-card-title">How the mood has moved</span>
        <div className="sv2-flex sv2-gap-10">
          <div className="sv2-segmented">
            {SCOPES.map((s) => (
              <button key={s.key} className={scope === s.key ? "active" : ""} onClick={() => setScope(s.key)}>
                {s.label}
              </button>
            ))}
          </div>
          <div className="sv2-segmented">
            {RANGES.map((r) => (
              <button key={r.key} className={days === r.key ? "active" : ""} onClick={() => setDays(r.key)}>
                {r.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div style={{ marginTop: 20, position: "relative" }}>
        {error ? (
          <ErrorState error={error} onRetry={refetch} title="Couldn't load the mood trend" />
        ) : loading ? (
          <div className="sv2-muted sv2-small" style={{ height: H, display: "flex", alignItems: "center", justifyContent: "center" }}>
            Loading trend…
          </div>
        ) : Object.keys(lineData).length === 0 ? (
          <div className="sv2-muted sv2-small" style={{ height: H, display: "flex", alignItems: "center", justifyContent: "center", textAlign: "center" }}>
            {scope === "crypto" || scope === "both"
              ? "Not enough sentiment history yet. Readings are stored each time the pipeline runs."
              : "There is no sentiment source for this market yet."}
          </div>
        ) : (
          <div
            ref={containerRef}
            style={{ position: "relative", cursor: "crosshair" }}
            onMouseMove={handleMouseMove}
            onMouseLeave={() => setHover(null)}
          >
            <svg width="100%" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet">
              <defs>
                {Object.keys(lineData).map((key) => (
                  <linearGradient key={key} id={`sv2TrendGrad-${key}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={lineColor[key]} stopOpacity={isMulti ? 0.08 : 0.18} />
                    <stop offset="100%" stopColor={lineColor[key]} stopOpacity="0" />
                  </linearGradient>
                ))}
              </defs>

              {/* Y axis: -100..+100, the same scale as the gauge. The zero line is the neutral point. */}
              {Y_TICKS.map((v) => {
                const y = PAD_T + plotH - ((v - MIN) / (MAX - MIN)) * plotH;
                return (
                  <g key={v}>
                    <line
                      x1={PAD_L} y1={y} x2={W - PAD_R} y2={y}
                      stroke="var(--sv2-border)"
                      strokeDasharray={v === 0 ? undefined : "3,3"}
                      opacity={v === 0 ? 1 : 0.6}
                    />
                    <text x={PAD_L - 8} y={y + 3.5} fontSize="10" textAnchor="end" fill="var(--sv2-text-mute)">
                      {signed(v)}
                    </text>
                  </g>
                );
              })}

              {/* X axis: dates of the time span the points are plotted over */}
              {xTicks.map((t, idx) => (
                <text key={idx} x={t.x} y={H - 6} fontSize="10" textAnchor="middle" fill="var(--sv2-text-mute)">
                  {t.label}
                </text>
              ))}

              {/* Area & Line Paths */}
              {Object.entries(lineData).map(([key, data]) => (
                <g key={key}>
                  {!isMulti && <path d={data.areaPath} fill={`url(#sv2TrendGrad-${key})`} />}
                  <path d={data.linePath} fill="none" stroke={lineColor[key]} strokeWidth={isMulti ? 2.2 : 2.6} strokeLinecap="round" />
                  <circle cx={data.last.x} cy={data.last.y} r="4.5" fill={lineColor[key]} stroke="#fff" strokeWidth="1.5" />
                </g>
              ))}

              {/* Hover Crosshair Line and Halo Points */}
              {hovered && hoverX != null && (
                <g>
                  <line x1={hoverX} y1={PAD_T} x2={hoverX} y2={PAD_T + plotH} stroke="var(--sv2-accent)" strokeWidth="1" strokeDasharray="3,3" opacity="0.75" />
                  {hovered.map(({ key, pt }) => (
                    <g key={`h-${key}`}>
                      <circle cx={pt.x} cy={pt.y} r="6.5" fill={lineColor[key]} opacity="0.25" />
                      <circle cx={pt.x} cy={pt.y} r="4" fill={lineColor[key]} stroke="#fff" strokeWidth="2" />
                    </g>
                  ))}
                </g>
              )}
            </svg>

            {/* Hover Tooltip Box — dated from the readings themselves */}
            {hovered && hoverX != null && (
              <div
                style={{
                  position: "absolute",
                  left: `${hoverFraction * 100}%`,
                  transform: hoverFraction < 0.12 ? "none" : hoverFraction > 0.88 ? "translateX(-100%)" : "translateX(-50%)",
                  top: 10,
                  background: "var(--sv2-card)",
                  border: "1px solid var(--sv2-border)",
                  borderRadius: 8,
                  padding: "5px 9px",
                  boxShadow: "0 4px 12px rgba(0,0,0,0.25)",
                  pointerEvents: "none",
                  zIndex: 20,
                  whiteSpace: "nowrap",
                }}
              >
                {hovered.map(({ key, pt }) => (
                  <div key={`tt-${key}`}>
                    <div style={{ fontSize: 10.5, color: "var(--sv2-text-mute)", fontWeight: 600 }}>{formatDate(pt.t)}</div>
                    <div style={{ fontSize: 12, color: lineColor[key], fontWeight: 800, display: "flex", alignItems: "center", gap: 5 }}>
                      <span style={{ width: 6, height: 6, borderRadius: "50%", background: lineColor[key] }} />
                      {LINE_META[key]?.label}: {signed(Math.round(pt.value))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="sv2-flex-between sv2-mt-8">
        <div className="sv2-flex sv2-gap-16" style={{ alignItems: "center", flexWrap: "wrap" }}>
          {Object.keys(lines).map((key) => (
            <div key={key} className="sv2-flex sv2-gap-8" style={{ alignItems: "center" }}>
              <span style={{ width: 20, height: 3, borderRadius: 2, background: lineColor[key], display: "inline-block" }} />
              <span className="sv2-small sv2-muted">{LINE_META[key]?.label}</span>
            </div>
          ))}
        </div>
        <span className="sv2-tiny sv2-mute2">Above 0 is net-positive sentiment</span>
      </div>
    </div>
  );
}
