import { deriveAaiSignal } from "../../services/assetDetailApi";
import { isMlUncertain } from "../../utils/scoring";

export default function AaiScoreCard({ aaiPanel, mlSignal }) {
  if (!aaiPanel) return null;
  const { score, confidence, note } = aaiPanel;
  const signal = deriveAaiSignal(score);
  const pct = Math.max(0, Math.min(100, score));
  // While the ML model has no direction call, the band is the AAI's rating, not a model Buy/Sell.
  const label = isMlUncertain(mlSignal) ? `AAI rating: ${signal.label}` : signal.label;

  return (
    <div className="sv2-card adt-panel-card">
      <div className="adt-panel-label">Alternative Asset Index</div>
      <div className="adt-aai-row">
        <span className="adt-aai-score">{Math.round(score)}</span>
        <div>
          <div className={`adt-aai-signal ${signal.tone}`}>{label.toUpperCase()}</div>
          {confidence != null && <div className="adt-panel-sub">{Math.round(confidence * 100)}% confidence</div>}
        </div>
      </div>
      <div className="adt-progress-track">
        <div className={`adt-progress-fill ${signal.tone}`} style={{ width: `${pct}%` }} />
      </div>
      <p className="adt-panel-desc">
        A composite of price behaviour, liquidity, sentiment and risk. It is a summary, not a
        verdict — the panels below are what it is made of.
      </p>
      {note && <p className="adt-panel-desc sv2-muted">{note}</p>}
    </div>
  );
}
