import { useState } from "react";
import { onHoldingsChanged } from "../../services/holdingsEvents";
import { useAsync } from "../../hooks/useAsync";
import { useElementSize } from "../../hooks/useElementSize";
import { dashboardApi } from "../../services/dashboardApi";
import { TIME_FILTERS } from "../../data/constants";
import TimeSeriesAreaChart from "../charts/TimeSeriesAreaChart";
import { ErrorState } from "../../errors";

export default function PortfolioPerformanceCard() {
  const [filter, setFilter] = useState("1M");
  const [containerRef, dims] = useElementSize({ W: 560, H: 220 });

  const { data: stats, error: statsError, refetch: refetchStats } = useAsync(() => dashboardApi.getMarketStats(), [], { subscribe: onHoldingsChanged });
  const { data: rawSeries, loading, error, refetch } = useAsync(() => dashboardApi.getPerformanceHistory(filter), [filter], { subscribe: onHoldingsChanged });
  const series = rawSeries || [];

  const hasHoldings = stats && stats.holdingsCount > 0;

  let chartContent = null;
  if (hasHoldings && series.length >= 2) {
    chartContent = <TimeSeriesAreaChart data={series} width={dims.W} height={dims.H} color="var(--sv2-accent)" gradientId="dv2PerfGrad" />;
  } else if (hasHoldings) {
    chartContent = (
      <div className="sv2-muted sv2-small" style={{ width: "100%", textAlign: "center" }}>
        No portfolio history has been recorded for this range yet.
      </div>
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

      <div style={{ height: "var(--dv2-perf-h, 260px)", display: "flex", flexDirection: "column", justifyContent: "center" }}>
        {statsError ? (
          <ErrorState error={statsError} onRetry={refetchStats} variant="panel" title="Couldn't check your holdings" />
        ) : !hasHoldings ? (
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
        ) : error ? (
          <ErrorState error={error} onRetry={refetch} variant="panel" title="Couldn't load performance" />
        ) : (
          <div ref={containerRef} style={{ width: "100%", height: "100%", display: "flex", alignItems: "center" }}>{chartContent}</div>
        )}
      </div>
    </div>
  );
}