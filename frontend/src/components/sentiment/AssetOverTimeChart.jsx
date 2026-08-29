import { useState, useRef } from "react";
import { useAsync } from "../../hooks/useAsync";
import { sentimentApi } from "../../services/sentimentApi";

const RANGES = [
  { key: "24h", label: "24h" },
  { key: 7, label: "7d" },
  { key: 30, label: "30d" },
  { key: 90, label: "90d" },
];

const TREND_TEXT = { improving: "Warming up", deteriorating: "Cooling down", stable: "Stable" };

function formatDateLabel(dStr) {
  if (!dStr) return "";
  const d = new Date(dStr);
  if (isNaN(d.getTime())) return String(dStr);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export default function AssetOverTimeChart({ assetId, trend, colors }) {
  const [range, setRange] = useState(30);
  const [hoverIdx, setHoverIdx] = useState(null);
  const containerRef = useRef(null);

  const { data: rawSeries, loading } = useAsync(() => sentimentApi.getAssetOverTime(assetId, range), [assetId, range]);
  const series = rawSeries || [];

  const W = 420, H = 170;
  const PAD_L = 32, PAD_R = 12, PAD_T = 12, PAD_B = 26;
  const plotW = W - PAD_L - PAD_R;
  const plotH = H - PAD_T - PAD_B;

  const color = trend === "deteriorating" ? colors.red : colors.green;

  // Extract numerical values & calculate clean bounds
  const values = series.map((s) => (typeof s === "number" ? s : s?.value ?? s?.score ?? 50));
  const rawMin = values.length ? Math.min(...values) : 0;
  const rawMax = values.length ? Math.max(...values) : 100;
  const minVal = Math.max(0, Math.floor(rawMin - 5));
  const maxVal = Math.min(100, Math.ceil(rawMax + 5));
  const rangeVal = Math.max(1, maxVal - minVal);

  const yTicks = [0, 1, 2, 3].map((i) => Math.round(minVal + (rangeVal * i) / 3));

  const pts = values.map((v, i) => {
    const x = PAD_L + (i / Math.max(1, values.length - 1)) * plotW;
    const y = PAD_T + plotH - ((v - minVal) / rangeVal) * plotH;
    return { x, y, value: v, date: series[i]?.date || series[i]?.timestamp };
  });

  const linePath = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
  const areaPath = pts.length ? `${linePath} L ${pts[pts.length - 1].x.toFixed(1)} ${PAD_T + plotH} L ${pts[0].x.toFixed(1)} ${PAD_T + plotH} Z` : "";

  const handleMouseMove = (e) => {
    if (!containerRef.current || !pts.length) return;
    const rect = containerRef.current.getBoundingClientRect();
    const mouseX = ((e.clientX - rect.left) / rect.width) * W;

    let closest = 0;
    let minDiff = Infinity;
    pts.forEach((pt, i) => {
      const diff = Math.abs(pt.x - mouseX);
      if (diff < minDiff) {
        minDiff = diff;
        closest = i;
      }
    });
    setHoverIdx(closest);
  };

  const hoverPt = hoverIdx != null ? pts[hoverIdx] : null;

  // Generate X axis ticks
  const xTicks = [];
  if (pts.length >= 2) {
    [0, Math.floor((pts.length - 1) / 2), pts.length - 1].forEach((idx) => {
      const pt = pts[idx];
      if (pt) xTicks.push({ x: pt.x, label: formatDateLabel(pt.date) });
    });
  }

  return (
    <div className="sv2-card sv2-card-pad-sm" style={{ position: "relative" }}>
      <div className="sv2-flex-between">
        <span className="sv2-card-title">Over time</span>
        <div className="sv2-segmented">
          {RANGES.map((r) => (
            <button key={r.key} className={range === r.key ? "active" : ""} onClick={() => setRange(r.key)}>{r.label}</button>
          ))}
        </div>
      </div>
      <div className="sv2-small sv2-mt-8" style={{ color, fontWeight: 700 }}>{TREND_TEXT[trend] ?? "Stable"}</div>
      
      <div className="sv2-mt-8" style={{ position: "relative" }}>
        {loading ? (
          <div className="sv2-muted sv2-small" style={{ height: H, display: "flex", alignItems: "center", justifyContent: "center" }}>Loading…</div>
        ) : (
          <div
            ref={containerRef}
            style={{ position: "relative", cursor: "crosshair" }}
            onMouseMove={handleMouseMove}
            onMouseLeave={() => setHoverIdx(null)}
          >
            <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
              <defs>
                <linearGradient id="sv2OverTimeGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity="0.22" />
                  <stop offset="100%" stopColor={color} stopOpacity="0" />
                </linearGradient>
              </defs>

              {/* Y Axis Grid & Labels */}
              {yTicks.map((v) => {
                const y = PAD_T + plotH - ((v - minVal) / rangeVal) * plotH;
                return (
                  <g key={v}>
                    <line x1={PAD_L} y1={y} x2={W - PAD_R} y2={y} stroke="var(--sv2-border)" strokeDasharray="3,3" opacity="0.5" />
                    <text x={PAD_L - 6} y={y + 3.5} fontSize="9.5" textAnchor="end" fill="var(--sv2-text-mute)">
                      {v}
                    </text>
                  </g>
                );
              })}

              {/* X Axis Date Ticks */}
              {xTicks.map((t, i) => (
                <text key={i} x={t.x} y={H - 5} fontSize="9.5" textAnchor="middle" fill="var(--sv2-text-mute)">
                  {t.label}
                </text>
              ))}

              <path d={areaPath} fill="url(#sv2OverTimeGrad)" />
              <path d={linePath} fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" />

              {/* Hover Guide & Point Highlight */}
              {hoverPt && (
                <g>
                  <line x1={hoverPt.x} y1={PAD_T} x2={hoverPt.x} y2={PAD_T + plotH} stroke={color} strokeWidth="1" strokeDasharray="3,3" opacity="0.75" />
                  <circle cx={hoverPt.x} cy={hoverPt.y} r="6" fill={color} opacity="0.25" />
                  <circle cx={hoverPt.x} cy={hoverPt.y} r="3.5" fill={color} stroke="#fff" strokeWidth="1.5" />
                </g>
              )}
            </svg>

            {/* Hover Tooltip Box */}
            {hoverPt && (
              <div
                style={{
                  position: "absolute",
                  left: Math.min(Math.max((hoverPt.x / W) * (containerRef.current?.clientWidth || W) - 45, 5), (containerRef.current?.clientWidth || W) - 105),
                  top: 5,
                  background: "var(--sv2-card)",
                  border: "1px solid var(--sv2-border)",
                  borderRadius: 7,
                  padding: "4px 8px",
                  boxShadow: "0 4px 12px rgba(0,0,0,0.25)",
                  pointerEvents: "none",
                  zIndex: 20,
                  whiteSpace: "nowrap",
                }}
              >
                <div style={{ fontSize: 9.5, color: "var(--sv2-text-mute)", fontWeight: 600 }}>{formatDateLabel(hoverPt.date)}</div>
                <div style={{ fontSize: 11.5, color, fontWeight: 800 }}>Score: {Math.round(hoverPt.value)}</div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}