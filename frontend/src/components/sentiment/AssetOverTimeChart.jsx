import { useState } from "react";
import { useAsync } from "../../hooks/useAsync";
import { sentimentApi } from "../../services/sentimentApi";

const RANGES = [
  { key: "24h", label: "24h" },
  { key: 7, label: "7d" },
  { key: 30, label: "30d" },
  { key: 90, label: "90d" },
];

const TREND_TEXT = { improving: "Warming up", deteriorating: "Cooling down", stable: "Stable" };

export default function AssetOverTimeChart({ assetId, trend, colors }) {
  const [range, setRange] = useState(30);
  const { data: rawSeries, loading } = useAsync(() => sentimentApi.getAssetOverTime(assetId, range), [assetId, range]);
  const series = rawSeries || [];

  const W = 420, H = 150;
  let linePath = "", areaPath = "";
  const color = trend === "deteriorating" ? colors.red : colors.green;

  if (series.length >= 2) {
    const values = series.map((s) => s.value);
    const min = Math.min(...values) - 3, max = Math.max(...values) + 3, range2 = Math.max(1, max - min);
    const pts = series.map((s, i) => ({ x: (i / (series.length - 1)) * W, y: H - 14 - ((s.value - min) / range2) * (H - 26) }));
    linePath = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
    areaPath = `${linePath} L ${pts[pts.length - 1].x.toFixed(1)} ${H} L ${pts[0].x.toFixed(1)} ${H} Z`;
  }

  return (
    <div className="sv2-card sv2-card-pad-sm">
      <div className="sv2-flex-between">
        <span className="sv2-card-title">Over time</span>
        <div className="sv2-segmented">
          {RANGES.map((r) => (
            <button key={r.key} className={range === r.key ? "active" : ""} onClick={() => setRange(r.key)}>{r.label}</button>
          ))}
        </div>
      </div>
      <div className="sv2-small sv2-mt-8" style={{ color, fontWeight: 700 }}>{TREND_TEXT[trend] ?? "Stable"}</div>
      <div className="sv2-mt-8">
        {loading ? (
          <div className="sv2-muted sv2-small" style={{ height: H, display: "flex", alignItems: "center", justifyContent: "center" }}>Loading…</div>
        ) : (
          <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
            <defs>
              <linearGradient id="sv2OverTimeGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity="0.22" />
                <stop offset="100%" stopColor={color} stopOpacity="0" />
              </linearGradient>
            </defs>
            <path d={areaPath} fill="url(#sv2OverTimeGrad)" />
            <path d={linePath} fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" />
          </svg>
        )}
      </div>
    </div>
  );
}