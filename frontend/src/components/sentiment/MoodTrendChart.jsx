import { useState, useRef } from "react";
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

function formatDateLabel(dStr) {
  if (!dStr) return "";
  const d = new Date(dStr);
  if (isNaN(d.getTime())) return String(dStr);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function buildPathWithPadding(values, W, H, PAD_L, PAD_R, PAD_T, PAD_B, min, max) {
  const plotW = W - PAD_L - PAD_R;
  const plotH = H - PAD_T - PAD_B;
  const range = Math.max(1, max - min);

  const pts = values.map((v, i) => {
    const x = PAD_L + (i / Math.max(1, values.length - 1)) * plotW;
    const y = PAD_T + plotH - ((v - min) / range) * plotH;
    return { x, y, value: v };
  });

  const linePath = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
  const areaPath = `${linePath} L ${pts[pts.length - 1].x.toFixed(1)} ${PAD_T + plotH} L ${pts[0].x.toFixed(1)} ${PAD_T + plotH} Z`;
  const last = pts[pts.length - 1];
  return { linePath, areaPath, last, pts };
}

export default function MoodTrendChart({ colors }) {
  const [scope, setScope] = useState("crypto");
  const [days, setDays] = useState(30);
  const [hoverIdx, setHoverIdx] = useState(null);
  const containerRef = useRef(null);

  const { data: series, loading } = useAsync(() => sentimentApi.getMoodTrend(scope, days), [scope, days]);

  const W = 900, H = 220;
  const PAD_L = 36, PAD_R = 16, PAD_T = 16, PAD_B = 28;
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

  const allValues = Object.values(lines).flat().map((p) => p.value);
  const min = 0;
  const max = 100;

  // Primary list of items to sample dates and point positions
  const primaryKey = Object.keys(lines)[0];
  const primaryList = primaryKey ? lines[primaryKey] : [];

  const handleMouseMove = (e) => {
    if (!containerRef.current || !primaryList?.length) return;
    const rect = containerRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const svgX = (mouseX / rect.width) * W;

    let closest = 0;
    let minDiff = Infinity;
    primaryList.forEach((_, i) => {
      const ptX = PAD_L + (i / Math.max(1, primaryList.length - 1)) * plotW;
      const diff = Math.abs(ptX - svgX);
      if (diff < minDiff) {
        minDiff = diff;
        closest = i;
      }
    });
    setHoverIdx(closest);
  };

  // Generate X-axis ticks (5 evenly spaced ticks across date range)
  const xTicks = [];
  if (primaryList?.length >= 2) {
    const count = 5;
    const now = new Date();
    for (let c = 0; c < count; c++) {
      const fraction = c / (count - 1);
      const idx = Math.round(fraction * (primaryList.length - 1));
      const pt = primaryList[idx];
      const x = PAD_L + fraction * plotW;

      // Calculate distinct date if raw dates are missing or uniform
      const daysAgo = Math.round((1 - fraction) * days);
      const tickDate = new Date(now.getTime() - daysAgo * 86400000);
      const formattedDate = pt?.date && primaryList[0]?.date !== primaryList[primaryList.length - 1]?.date
        ? formatDateLabel(pt.date)
        : tickDate.toLocaleDateString("en-US", { month: "short", day: "numeric" });

      xTicks.push({ x, label: formattedDate });
    }
  }

  // Precompute line paths and points
  const lineData = {};
  Object.entries(lines).forEach(([key, values]) => {
    if (values && values.length >= 2) {
      lineData[key] = buildPathWithPadding(values.map((v) => v.value), W, H, PAD_L, PAD_R, PAD_T, PAD_B, min, max);
    }
  });

  const hoverX = hoverIdx != null && primaryList.length
    ? PAD_L + (hoverIdx / Math.max(1, primaryList.length - 1)) * plotW
    : null;

  const hoverDate = hoverIdx != null && primaryList.length
    ? (() => {
        const fraction = hoverIdx / Math.max(1, primaryList.length - 1);
        const daysAgo = Math.round((1 - fraction) * days);
        const d = new Date();
        d.setDate(d.getDate() - daysAgo);
        return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
      })()
    : "";

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
        {loading || Object.keys(lines).length === 0 ? (
          <div className="sv2-muted sv2-small" style={{ height: H, display: "flex", alignItems: "center", justifyContent: "center" }}>
            Loading trend…
          </div>
        ) : (
          <div
            ref={containerRef}
            style={{ position: "relative", cursor: "crosshair" }}
            onMouseMove={handleMouseMove}
            onMouseLeave={() => setHoverIdx(null)}
          >
            <svg width="100%" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet">
              <defs>
                {Object.keys(lines).map((key) => (
                  <linearGradient key={key} id={`sv2TrendGrad-${key}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={lineColor[key]} stopOpacity={isMulti ? 0.08 : 0.18} />
                    <stop offset="100%" stopColor={lineColor[key]} stopOpacity="0" />
                  </linearGradient>
                ))}
              </defs>

              {/* Y Axis Grid & Labels */}
              {[0, 25, 50, 75, 100].map((v) => {
                const y = PAD_T + plotH - (v / 100) * plotH;
                return (
                  <g key={v}>
                    <line x1={PAD_L} y1={y} x2={W - PAD_R} y2={y} stroke="var(--sv2-border)" strokeDasharray="3,3" opacity="0.6" />
                    <text x={PAD_L - 8} y={y + 3.5} fontSize="10" textAnchor="end" fill="var(--sv2-text-mute)">
                      {v}
                    </text>
                  </g>
                );
              })}

              {/* X Axis Date Ticks */}
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
              {hoverIdx != null && hoverX != null && (
                <g>
                  <line x1={hoverX} y1={PAD_T} x2={hoverX} y2={PAD_T + plotH} stroke="var(--sv2-accent)" strokeWidth="1" strokeDasharray="3,3" opacity="0.75" />
                  {Object.entries(lineData).map(([key, data]) => {
                    const pt = data.pts[hoverIdx];
                    if (!pt) return null;
                    return (
                      <g key={`h-${key}`}>
                        <circle cx={pt.x} cy={pt.y} r="6.5" fill={lineColor[key]} opacity="0.25" />
                        <circle cx={pt.x} cy={pt.y} r="4" fill={lineColor[key]} stroke="#fff" strokeWidth="2" />
                      </g>
                    );
                  })}
                </g>
              )}
            </svg>

            {/* Hover Tooltip Box */}
            {hoverIdx != null && hoverX != null && (
              <div
                style={{
                  position: "absolute",
                  left: Math.min(Math.max((hoverX / W) * (containerRef.current?.clientWidth || W) - 60, 10), (containerRef.current?.clientWidth || W) - 140),
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
                <div style={{ fontSize: 10.5, color: "var(--sv2-text-mute)", fontWeight: 600 }}>{hoverDate}</div>
                {Object.entries(lineData).map(([key, data]) => {
                  const val = data.pts[hoverIdx]?.value;
                  if (val == null) return null;
                  return (
                    <div key={`tt-${key}`} style={{ fontSize: 12, color: lineColor[key], fontWeight: 800, display: "flex", alignItems: "center", gap: 5 }}>
                      <span style={{ width: 6, height: 6, borderRadius: "50%", background: lineColor[key] }} />
                      {LINE_META[key]?.label}: {Math.round(val)}
                    </div>
                  );
                })}
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
        <span className="sv2-tiny sv2-mute2">Above 50 is net-positive sentiment</span>
      </div>
    </div>
  );
}