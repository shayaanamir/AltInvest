import { useState, useEffect, useRef } from "react";
import { dashboardApi } from "../../services/dashboardApi";
import { TIME_FILTERS } from "../../data/constants";

export default function PortfolioPerformanceCard() {
  const [filter, setFilter] = useState("1M");
  const [stats, setStats] = useState(null);
  const [series, setSeries] = useState([]);
  const [loading, setLoading] = useState(true);
  const containerRef = useRef(null);
  const [dims, setDims] = useState({ W: 560, H: 220 });

  useEffect(() => {
    dashboardApi.getMarketStats().then(setStats).catch(console.error);
  }, []);

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
    dashboardApi.getPerformanceHistory(filter).then((s) => {
      setSeries(s);
      setLoading(false);
    }).catch(console.error);
  }, [filter]);

  const hasHoldings = stats && stats.holdingsCount > 0;
  const { W, H } = dims;

  let chartContent = null;
  if (hasHoldings && series.length >= 2) {
    const vals = series.map((d) => d.value);
    const min = Math.min(...vals) * 0.98;
    const max = Math.max(...vals) * 1.02;
    const range = Math.max(1, max - min);
    const toPoint = (v, i) => ({
      x: 10 + (i / (series.length - 1)) * (W - 20),
      y: H - 16 - ((v - min) / range) * (H - 30),
    });
    const pts = series.map((d, i) => toPoint(d.value, i));
    const last = pts[pts.length - 1];
    const linePath = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
    const areaPath = `${linePath} L ${last.x.toFixed(1)} ${H} L ${pts[0].x.toFixed(1)} ${H} Z`;

    chartContent = (
      <svg width="100%" height="100%" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
        <defs>
          <linearGradient id="dv2PerfGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--sv2-accent)" stopOpacity="0.25" />
            <stop offset="100%" stopColor="var(--sv2-accent)" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={areaPath} fill="url(#dv2PerfGrad)" />
        <path d={linePath} fill="none" stroke="var(--sv2-accent)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx={last.x} cy={last.y} r="4" fill="var(--sv2-accent)" />
      </svg>
    );
  }

  return (
    <div className="sv2-card sv2-card-pad">
      <div className="dv2-perf-head">
        <span className="sv2-card-title">Portfolio performance</span>
        <div className="sv2-segmented">
          {TIME_FILTERS.map((f) => (
            <button key={f} className={filter === f ? "active" : ""} onClick={() => setFilter(f)}>{f}</button>
          ))}
        </div>
      </div>

      <div style={{ height: 260 }}>
        {!hasHoldings ? (
          <div className="dv2-perf-empty" style={{ height: "100%" }}>
            <div className="dv2-perf-empty-icon" aria-hidden="true">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M23 6l-9.5 9.5-5-5L1 18" />
                <path d="M17 6h6v6" />
              </svg>
            </div>
            <div className="dv2-perf-empty-text">Add a holding to see performance</div>
          </div>
        ) : loading ? (
          <div className="sv2-muted sv2-small" style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
            Loading…
          </div>
        ) : (
          <div ref={containerRef} style={{ width: "100%", height: "100%" }}>{chartContent}</div>
        )}
      </div>
    </div>
  );
}