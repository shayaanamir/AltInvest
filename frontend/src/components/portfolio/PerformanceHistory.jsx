import { useState, useEffect, useRef } from "react";
import { portfolioApi } from "../../services/portfolioApi";

const RANGES = ["1M", "3M", "1Y"];

export default function PerformanceHistory() {
  const [range, setRange] = useState("3M");
  const [series, setSeries] = useState([]);
  const [loading, setLoading] = useState(true);
  const containerRef = useRef(null);
  const [dims, setDims] = useState({ W: 560, H: 220 });

  useEffect(() => {
    const ob = new ResizeObserver((entries) => {
      if (entries[0]) {
        setDims({
          W: Math.max(120, entries[0].contentRect.width),
          H: Math.max(120, entries[0].contentRect.height),
        });
      }
    });
    if (containerRef.current) ob.observe(containerRef.current);
    return () => ob.disconnect();
  }, []);

  useEffect(() => {
    setLoading(true);
    portfolioApi.getPerformanceHistory(range).then((s) => {
      setSeries(s);
      setLoading(false);
    }).catch(console.error);
  }, [range]);

  const { W, H } = dims;
  const PAD_L = 46, PAD_R = 10, PAD_T = 10, PAD_B = 22;

  let content = null;

  if (!loading && series.length >= 2) {
    const now = Date.now();
    const vals = series.map((d) => d.value);
    const minVal = Math.min(...vals) * 0.98;
    const maxVal = Math.max(...vals) * 1.02;
    const range2 = Math.max(1, maxVal - minVal);

    const toPoint = (v, i) => ({
      x: PAD_L + (i / (series.length - 1)) * (W - PAD_L - PAD_R),
      y: H - PAD_B - ((v - minVal) / range2) * (H - PAD_T - PAD_B),
    });
    const pts = series.map((d, i) => toPoint(d.value, i));
    const last = pts[pts.length - 1];
    const linePath = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
    const areaPath = `${linePath} L ${last.x.toFixed(1)} ${H - PAD_B} L ${pts[0].x.toFixed(1)} ${H - PAD_B} Z`;

    const yLabels = [0, 1, 2, 3].map((i) => minVal + (range2 * i) / 3);
    const xIdxs = [0, Math.floor((series.length - 1) / 2), series.length - 1];

    const formatY = (v) => (v >= 1000 ? `$${(v / 1000).toFixed(1)}K` : `$${v.toFixed(0)}`);
    const daysAgo = (dateStr) => {
      const diff = Math.round((now - new Date(dateStr).getTime()) / 86400000);
      return diff <= 0 ? "Today" : `${diff}d`;
    };

    content = (
      <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
        <defs>
          <linearGradient id="pv2PerfGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--sv2-accent)" stopOpacity="0.28" />
            <stop offset="100%" stopColor="var(--sv2-accent)" stopOpacity="0" />
          </linearGradient>
        </defs>

        {yLabels.map((v, i) => {
          const y = H - PAD_B - ((v - minVal) / range2) * (H - PAD_T - PAD_B);
          return (
            <g key={i}>
              <line x1={PAD_L} y1={y} x2={W - PAD_R} y2={y} stroke="var(--sv2-grey-arc)" strokeWidth="0.7" strokeDasharray="4,4" />
              <text x={PAD_L - 8} y={y + 4} fontSize="9.5" fill="var(--sv2-grey-arc)" textAnchor="end">{formatY(v)}</text>
            </g>
          );
        })}

        {xIdxs.map((idx, i) => (
          <text key={i} x={pts[idx].x} y={H - 5} fontSize="9.5" fill="var(--sv2-grey-arc)" textAnchor="middle">
            {daysAgo(series[idx].date)}
          </text>
        ))}

        <path d={areaPath} fill="url(#pv2PerfGrad)" />
        <path d={linePath} fill="none" stroke="var(--sv2-accent)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx={last.x} cy={last.y} r="4" fill="var(--sv2-accent)" />
      </svg>
    );
  } else if (!loading) {
    content = (
      <div className="sv2-muted sv2-small" style={{ height: H, display: "flex", alignItems: "center", justifyContent: "center" }}>
        Not enough data
      </div>
    );
  }

  return (
    <div className="sv2-card sv2-card-pad">
      <div className="dv2-perf-head">
        <span className="sv2-card-title">Performance history</span>
        <div className="sv2-segmented">
          {RANGES.map((r) => (
            <button key={r} className={range === r ? "active" : ""} onClick={() => setRange(r)}>{r}</button>
          ))}
        </div>
      </div>
      <div style={{ height: 240, position: "relative" }} ref={containerRef}>
        {loading ? (
          <div className="sv2-muted sv2-small" style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
            Loading…
          </div>
        ) : content}
      </div>
    </div>
  );
}