import { deriveAaiSignal } from "../../services/assetDetailApi";
import { DISCLAIMER_SHORT } from "../layout/Disclaimer";

export default function AaiScoreCard({ aaiPanel }) {
  if (!aaiPanel) return null;
  const { score, confidence, note, staleInputs = [], asOf } = aaiPanel;

  // No score: its prediction or risk input is too old (audit G-20) or missing. Say which, never draw a number.
  if (score == null) {
    return (
      <div className="sv2-card adt-panel-card">
        <div className="adt-panel-label">Alternative Asset Index</div>
        <div className="adt-aai-row">
          <span className="adt-aai-score">—</span>
          <div className="adt-aai-signal">{staleInputs.length ? "INPUTS STALE" : "NOT AVAILABLE"}</div>
        </div>
        {note && <p className="adt-panel-desc sv2-muted">{note}</p>}
        <p className="adt-panel-desc sv2-small sv2-muted">{DISCLAIMER_SHORT}</p>
      </div>
    );
  }

  const signal = deriveAaiSignal(score);
  const pct = Math.max(0, Math.min(100, score));
  // Always a rating, never a Buy/Sell call (audit G-37).
  const label = `AAI rating: ${signal.label}`;

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
      {asOf && <p className="adt-panel-desc sv2-small sv2-muted">Inputs as of {asOf.slice(0, 16).replace("T", " ")} UTC</p>}
      {note && <p className="adt-panel-desc sv2-muted">{note}</p>}
      <p className="adt-panel-desc sv2-small sv2-muted">{DISCLAIMER_SHORT}</p>
    </div>
  );
}
