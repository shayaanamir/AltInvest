import { useEffect } from "react";
import { useAsync } from "../../hooks/useAsync";
import { loadPortfolioAnalysis } from "../../services/analysisApi";
import { formatCurrencyFull, formatPct } from "../../utils/formatters";
import { ErrorState } from "../../errors";
import "../portfolio/addHoldingModal.css";
import "./portfolioAnalysis.css";

const row = (label, value) => (
  <div className="pa-row">
    <span className="pa-label">{label}</span>
    <span className="pa-value">{value}</span>
  </div>
);

/** Read-out of the signed-in user's portfolio, computed from their holdings and the stored scores. */
export default function PortfolioAnalysisModal({ onClose, onAddHolding }) {
  const { data, loading, error, refetch } = useAsync(() => loadPortfolioAnalysis(), []);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const a = data;
  const signals = a ? Object.entries(a.intel.signalMix || {}) : [];

  return (
    <div className="ahm-overlay" onClick={onClose}>
      <div className="ahm pa" role="dialog" aria-modal="true" aria-label="Portfolio analysis" onClick={(e) => e.stopPropagation()}>
        <div className="ahm-head">
          <h2>Portfolio analysis</h2>
          <button type="button" className="ahm-close" aria-label="Close" onClick={onClose}>×</button>
        </div>
        <p className="ahm-desc">
          Worked out from what you hold and the AAI, risk and sentiment scores stored for each asset.
          It describes your portfolio as it stands; it is not a forecast or financial advice.
        </p>

        {error ? (
          <ErrorState error={error} onRetry={refetch} variant="panel" title="Couldn't analyse your portfolio" />
        ) : loading || !a ? (
          <div className="ahm-empty">Analysing…</div>
        ) : a.empty ? (
          <div className="pa-empty">
            <p>There is nothing to analyse yet — you haven't recorded any holdings.</p>
            <button type="button" className="ahm-submit" onClick={() => { onClose(); onAddHolding?.(); }}>Add a holding</button>
          </div>
        ) : (
          <>
            <div className="pa-section">
              {row("Total value", formatCurrencyFull(a.totalValue))}
              {row("Positions", a.positions.length)}
              {row("Unrealised P&L", `${formatCurrencyFull(a.summary.totalProfitLoss)} (${formatPct(a.summary.totalProfitLossPct, { withSign: true })})`)}
              {row("Value-weighted AAI score", a.weightedAai != null ? Math.round(a.weightedAai) : "No scored holdings")}
              {a.intel.aggregateRiskScore != null && row("Average risk score", `${a.intel.aggregateRiskScore}/100 (higher means lower risk)`)}
              {a.intel.sentimentExposure != null && row("Average sentiment", `${a.intel.sentimentExposure > 0 ? "+" : ""}${a.intel.sentimentExposure}`)}
              {signals.length > 0 && row("Signal mix", signals.map(([k, n]) => `${k} ×${n}`).join(" · "))}
            </div>

            <h3 className="pa-h">What stands out</h3>
            <ul className="pa-list">
              {a.largest && (
                <li>
                  <strong>{a.largest.label}</strong> is {a.largest.sharePct.toFixed(0)}% of your portfolio
                  {a.concentrated ? " — a heavy concentration in one position." : "."}
                </li>
              )}
              {a.strongest && (
                <li>Highest AAI score: <strong>{a.strongest.label}</strong> ({Math.round(a.strongest.aaiScore)}).</li>
              )}
              {a.weakest && (
                <li>Lowest AAI score: <strong>{a.weakest.label}</strong> ({Math.round(a.weakest.aaiScore)}).</li>
              )}
              {a.toReduce.length > 0 && (
                <li>The current signal suggests reducing: {a.toReduce.map((p) => p.label).join(", ")}.</li>
              )}
              {a.unscored.length > 0 && (
                <li>No stored score for {a.unscored.map((p) => p.label).join(", ")}, so they are left out of the averages above.</li>
              )}
            </ul>

            <h3 className="pa-h">Largest positions</h3>
            <div className="pa-section">
              {a.positions.slice(0, 5).map((p) => (
                <div className="pa-row" key={`${p.kind}-${p.label}`}>
                  <span className="pa-label">{p.label}</span>
                  <span className="pa-value">{p.sharePct.toFixed(1)}% · AAI {p.aaiScore != null ? Math.round(p.aaiScore) : "—"}</span>
                </div>
              ))}
            </div>
          </>
        )}

        <div className="ahm-footer">
          <button type="button" className="ahm-submit" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
