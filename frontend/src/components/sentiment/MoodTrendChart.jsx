import { useState, useEffect } from "react";
import { sentimentApi } from "../../services/sentimentApi";

const SCOPES = [
  { key: "crypto", label: "Crypto" },
  { key: "nft", label: "NFTs" },
  { key: "both", label: "Both" },
];
const RANGES = [
  { key: 7, label: "7d" },
  { key: 30, label: "30d" },
  { key: 90, label: "90d" },
];

export default function MoodTrendChart({ colors }) {
  const [scope, setScope] = useState("crypto");
  const [days, setDays] = useState(30);
  const [series, setSeries] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    sentimentApi.getMoodTrend(scope, days).then((s) => {
      setSeries(s);
      setLoading(false);
    }).catch(console.error);
  }, [scope, days]);

  const W = 900, H = 190;
  let linePath = "", areaPath = "";

  if (series.length >= 2) {
    const values = series.map((s) => s.value);
    const min = Math.min(...values) - 4;
    const max = Math.max(...values) + 4;
    const range = Math.max(1, max - min);
    const pts = series.map((s, i) => ({
      x: (i / (series.length - 1)) * W,
      y: H - 24 - ((s.value - min) / range) * (H - 40),
    }));
    linePath = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
    areaPath = `${linePath} L ${pts[pts.length - 1].x.toFixed(1)} ${H} L ${pts[0].x.toFixed(1)} ${H} Z`;
  }

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
        {loading ? (
          <div className="sv2-muted sv2-small" style={{ height: H, display: "flex", alignItems: "center", justifyContent: "center" }}>
            Loading trend…
          </div>
        ) : (
          <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
            <defs>
              <linearGradient id="sv2TrendGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={colors.accent} stopOpacity="0.16" />
                <stop offset="100%" stopColor={colors.accent} stopOpacity="0" />
              </linearGradient>
            </defs>
            <line x1="0" y1={H - 24} x2={W} y2={H - 24} stroke={colors.border} strokeWidth="1" />
            <path d={areaPath} fill="url(#sv2TrendGrad)" />
            <path d={linePath} fill="none" stroke={colors.accent} strokeWidth="2.5" strokeLinecap="round" />
            {series.length > 0 && (() => {
              const last = series.length - 1;
              const values = series.map((s) => s.value);
              const min = Math.min(...values) - 4, max = Math.max(...values) + 4, range = Math.max(1, max - min);
              const x = (last / (series.length - 1)) * W;
              const y = H - 24 - ((series[last].value - min) / range) * (H - 40);
              return <circle cx={x} cy={y} r="5" fill={colors.accent} />;
            })()}
          </svg>
        )}
      </div>

      <div className="sv2-flex-between sv2-mt-8">
        <div className="sv2-flex sv2-gap-8" style={{ alignItems: "center" }}>
          <span style={{ width: 20, height: 3, borderRadius: 2, background: colors.accent, display: "inline-block" }} />
          <span className="sv2-small sv2-muted">{SCOPES.find((s) => s.key === scope)?.label}</span>
        </div>
        <span className="sv2-tiny sv2-mute2">Above the line is net-positive sentiment</span>
      </div>
    </div>
  );
}