import { useState, useEffect, useRef } from "react";
import { dashboardApi } from "../../services/dashboardApi";
import { TIME_FILTERS } from "../../data/constants";
import TimeSeriesAreaChart from "../charts/TimeSeriesAreaChart";

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

  let chartContent = null;
  if (hasHoldings && series.length >= 2) {
    chartContent = <TimeSeriesAreaChart data={series} width={dims.W} height={dims.H} color="var(--sv2-accent)" gradientId="dv2PerfGrad" />;
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