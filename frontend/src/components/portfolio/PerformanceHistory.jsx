import { useState, useEffect, useRef } from "react";
import { portfolioApi } from "../../services/portfolioApi";
import TimeSeriesAreaChart from "../charts/TimeSeriesAreaChart";

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

  const daysAgo = (dateStr) => {
    const diff = Math.round((Date.now() - new Date(dateStr).getTime()) / 86400000);
    return diff <= 0 ? "Today" : `${diff}d`;
  };

  let content = null;

  if (!loading && series.length >= 2) {
    content = (
      <TimeSeriesAreaChart
        data={series}
        width={W}
        height={H}
        color="var(--sv2-accent)"
        gradientId="pv2PerfGrad"
        xLabelFormatter={daysAgo}
      />
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