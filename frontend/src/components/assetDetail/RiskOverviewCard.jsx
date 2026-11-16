import { riskLevelTone } from "../../services/assetDetailApi";

export default function RiskOverviewCard({ riskOverview }) {
  // No stored breakdown (the seeded one was removed, ml/docs/DECISIONS.md D94; measured values come later):
  // say so rather than hiding the panel or showing made-up numbers.
  if (!riskOverview || riskOverview.length === 0) {
    return (
      <div className="sv2-card adt-panel-card">
        <div className="adt-panel-label">Risk Overview</div>
        <div className="sv2-small sv2-muted">Risk breakdown not available yet.</div>
      </div>
    );
  }

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