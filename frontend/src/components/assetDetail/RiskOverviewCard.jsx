import { riskLevelTone } from "../../services/assetDetailApi";

export default function RiskOverviewCard({ riskOverview }) {
  if (!riskOverview || riskOverview.length === 0) return null;

  return (
    <div className="sv2-card adt-panel-card">
      <div className="adt-panel-label">Risk Overview</div>
      <div className="adt-risk-list">
        {riskOverview.map((r) => {
          const tone = riskLevelTone(r.level);
          return (
            <div key={r.label}>
              <div className="adt-risk-top">
                <span>{r.label}</span>
                <span className="adt-risk-value">{r.value}</span>
              </div>
              <div className="adt-progress-track sm">
                <div className={`adt-progress-fill ${tone}`} style={{ width: `${Math.min(100, r.value)}%` }} />
              </div>
              <div className="adt-risk-level">{r.level.charAt(0).toUpperCase() + r.level.slice(1)}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}