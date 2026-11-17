import { riskLevelTone } from "../../services/assetDetailApi";

// Raw values as measured (ml/docs/DECISIONS.md D96): volatility annualised, liquidity a ratio, drawdown a fall.
function formatRaw(r) {
  if (r.raw == null) return null;
  if (r.key === "liquidity") return `${(r.raw * 100).toFixed(2)}% of market cap traded in 24h`;
  if (r.key === "market_risk") return `${(r.raw * 100).toFixed(1)}% largest fall in 90 days`;
  if (r.key === "volatility") return `${(r.raw * 100).toFixed(1)}% annualised 30-day volatility`;
  return String(r.raw);
}

function tooltip(r) {
  const parts = [
    `${r.label}: safety score 0-100, higher = safer, ranked across ${r.ranked_among ?? "the"} covered coins.`,
    formatRaw(r),
    r.source && `Source: ${r.source}.`,
    r.as_of && `As of ${r.as_of.slice(0, 16).replace("T", " ")} UTC.`,
    r.value == null && r.why && `Not available: ${r.why}.`,
  ];
  return parts.filter(Boolean).join(" ");
}

export default function RiskOverviewCard({ riskOverview, riskCovered = true }) {
  if (!riskCovered) {
    return (
      <div className="sv2-card adt-panel-card">
        <div className="adt-panel-label">Risk Overview</div>
        <div className="sv2-small sv2-muted">Not covered: the risk model doesn't cover this asset.</div>
      </div>
    );
  }
  // No measured breakdown stored yet: say so rather than hiding the panel or showing made-up numbers.
  if (!riskOverview || riskOverview.length === 0) {
    return (
      <div className="sv2-card adt-panel-card">
        <div className="adt-panel-label">Risk Overview</div>
        <div className="sv2-small sv2-muted">Risk breakdown not available yet.</div>
      </div>
    );
  }

  const asOf = riskOverview.map((r) => r.as_of).filter(Boolean).sort()[0];
  return (
    <div className="sv2-card adt-panel-card">
      <div className="adt-panel-label">Risk Overview</div>
      <div className="sv2-small sv2-muted" style={{ marginBottom: 10 }}>Safety scores, 0-100: higher = safer.</div>
      <div className="adt-risk-list">
        {riskOverview.map((r) => {
          const available = r.value != null;
          const tone = available ? riskLevelTone(r.level) : "neutral";
          return (
            <div key={r.key || r.label} title={tooltip(r)}>
              <div className="adt-risk-top">
                <span>{r.label}</span>
                <span className="adt-risk-value">{available ? Math.round(r.value) : "—"}</span>
              </div>
              <div className="adt-progress-track sm">
                <div className={`adt-progress-fill ${tone}`} style={{ width: `${available ? Math.min(100, r.value) : 0}%` }} />
              </div>
              <div className="adt-risk-level">
                {available ? `${r.level.charAt(0).toUpperCase() + r.level.slice(1)} risk · ${formatRaw(r)}` : "Not available"}
              </div>
            </div>
          );
        })}
      </div>
      {asOf && <div className="adt-risk-level" style={{ marginTop: 10 }}>Measured data as of {asOf.slice(0, 10)}</div>}
    </div>
  );
}
