import { useState, useEffect } from "react";
import { portfolioApi } from "../../services/portfolioApi";
import { formatCurrencyFull, formatCurrencyWhole, formatPct } from "../../utils/formatters";

const RING_R = 30;
const RING_CIRC = 2 * Math.PI * RING_R;

function DiversificationRing({ score, color, track }) {
  const pct = Math.max(0, Math.min(100, score));
  const dash = (pct / 100) * RING_CIRC;
  return (
    <svg width="76" height="76" viewBox="0 0 76 76">
      <circle cx="38" cy="38" r={RING_R} fill="none" stroke={track} strokeWidth="7" />
      <circle
        cx="38" cy="38" r={RING_R} fill="none"
        stroke={color} strokeWidth="7" strokeLinecap="round"
        strokeDasharray={`${dash} ${RING_CIRC}`}
        transform="rotate(-90 38 38)"
      />
      <text x="38" y="35" textAnchor="middle" fontSize="18" fontWeight="800" fill="currentColor">
        {Math.round(score)}
      </text>
      <text x="38" y="49" textAnchor="middle" fontSize="7" fontWeight="700" letterSpacing="0.06em" fill="currentColor" opacity="0.55">
        SCORE
      </text>
    </svg>
  );
}

export default function PortfolioStats() {
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    portfolioApi.getSummary().then(setSummary).catch(console.error);
  }, []);

  if (!summary) {
    return (
      <div className="pv2-stats-grid">
        {[0, 1, 2].map((i) => (
          <div key={i} className="sv2-card dv2-stat-card sv2-muted sv2-small">Loading…</div>
        ))}
      </div>
    );
  }

  return (
    <div className="pv2-stats-grid">
      <div className="sv2-card dv2-stat-card">
        <div className="dv2-stat-label">Total Balance</div>
        <div className="dv2-stat-value">{formatCurrencyFull(summary.totalBalance)}</div>
        <div className="dv2-stat-sub">Cost basis {formatCurrencyWhole(summary.totalCostBasis)}</div>
      </div>

      <div className="sv2-card dv2-stat-card">
        <div className="dv2-stat-label">Total Profit / Loss</div>
        <div className="pv2-value-row">
          <span className="dv2-stat-value">
            {summary.totalProfitLossPositive ? "+" : "-"}
            {formatCurrencyWhole(Math.abs(summary.totalProfitLoss))}
          </span>
          <span className={`dv2-asset-change ${summary.totalProfitLossPositive ? "positive" : "negative"}`}>
            {summary.totalProfitLossPositive ? "↗" : "↘"} {formatPct(summary.totalProfitLossPct, { withSign: true })}
          </span>
        </div>
        <div className="dv2-stat-sub">Unrealised, across {summary.positionsCount} positions</div>
      </div>

      <div className="sv2-card dv2-stat-card pv2-diversification-card">
        <div className="pv2-ring-wrap">
          <DiversificationRing score={summary.diversificationScore} color="var(--sv2-accent)" track="var(--sv2-grey-arc)" />
        </div>
        <div className="pv2-diversification-text">
          <div className="dv2-stat-label">Diversification</div>
          <div className="pv2-diversification-title">{summary.diversificationLabel}</div>
          <div className={`pv2-diversification-note ${summary.needsRebalancing ? "warn" : ""}`}>
            {summary.rebalanceNote}
          </div>
        </div>
      </div>
    </div>
  );
}