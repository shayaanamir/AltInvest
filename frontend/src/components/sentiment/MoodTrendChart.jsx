import { useState, useEffect } from "react";
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
  crypto:     { label: "Crypto" },
  nft:        { label: "NFTs" },
  realEstate: { label: "Real Estate" },
};

function buildPath(values, W, H, min, max) {
  const range = Math.max(1, max - min);
  const pts = values.map((v, i) => ({
    x: (i / (values.length - 1)) * W,
    y: H - 24 - ((v - min) / range) * (H - 40),
  }));
  const linePath = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
  const areaPath = `${linePath} L ${pts[pts.length - 1].x.toFixed(1)} ${H} L ${pts[0].x.toFixed(1)} ${H} Z`;
  const last = pts[pts.length - 1];
  return { linePath, areaPath, last };
}

export default function MoodTrendChart({ colors }) {
  const [scope, setScope] = useState("crypto");
  const [days, setDays] = useState(30);
  const [series, setSeries] = useState(null);   // single-scope: array; "both": { crypto, nft, realEstate }
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    sentimentApi.getMoodTrend(scope, days).then((s) => {
      setSeries(s);
      setLoading(false);
    }).catch(console.error);
  }, [scope, days]);

  const W = 900, H = 190;
  const isMulti = scope === "both";

  // Normalize into { key: [{value}, ...] } shape for rendering, regardless of scope
  // Prevents crashes during transition state where scope is updated but series still holds stale data of a different type
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

  // Shared y-scale across all visible lines so they're comparable
  const allValues = Object.values(lines).flat().map((p) => p.value);
  const min = allValues.length ? Math.min(...allValues) - 4 : 0;
  const max = allValues.length ? Math.max(...allValues) + 4 : 1;

  return (
    <div className="sv2-card sv2-card-pad">
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

      <div style={{ marginTop: 20 }}>
        {loading || Object.keys(lines).length === 0 ? (
          <div className="sv2-muted sv2-small" style={{ height: H, display: "flex", alignItems: "center", justifyContent: "center" }}>
            Loading trend…
          </div>
        ) : (
          <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
            <defs>
              {Object.keys(lines).map((key) => (
                <linearGradient key={key} id={`sv2TrendGrad-${key}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={lineColor[key]} stopOpacity={isMulti ? 0.08 : 0.16} />
                  <stop offset="100%" stopColor={lineColor[key]} stopOpacity="0" />
                </linearGradient>
              ))}
            </defs>

            <line x1="0" y1={H - 24} x2={W} y2={H - 24} stroke={colors.border} strokeWidth="1" />

            {Object.entries(lines).map(([key, values]) => {
              if (!values || values.length < 2) return null;
              const { linePath, areaPath, last } = buildPath(values.map((v) => v.value), W, H, min, max);
              return (
                <g key={key}>
                  {!isMulti && <path d={areaPath} fill={`url(#sv2TrendGrad-${key})`} />}
                  <path d={linePath} fill="none" stroke={lineColor[key]} strokeWidth={isMulti ? 2.2 : 2.5} strokeLinecap="round" />
                  <circle cx={last.x} cy={last.y} r="5" fill={lineColor[key]} />
                </g>
              );
            })}
          </svg>
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
        <span className="sv2-tiny sv2-mute2">Above the line is net-positive sentiment</span>
      </div>
    </div>
  );
}