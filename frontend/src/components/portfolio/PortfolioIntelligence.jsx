import { useAsync } from "../../hooks/useAsync";
import { portfolioApi } from "../../services/portfolioApi";

export default function PortfolioIntelligence() {
  const { data: intel } = useAsync(() => portfolioApi.getIntelligence(), []);

  if (!intel) {
    return <div className="sv2-card sv2-card-pad sv2-muted sv2-small" style={{ marginTop: 10 }}>Loading…</div>;
  }

  const signalEntries = Object.entries(intel.signalMix || {});
  const suggestions = Array.isArray(intel.suggestions) ? intel.suggestions : [];
  const formattedSentiment =
    intel.sentimentExposure != null && !Number.isNaN(Number(intel.sentimentExposure))
      ? `${intel.sentimentExposure > 0 ? "+" : ""}${Number(intel.sentimentExposure).toFixed(2)}`
      : "—";

  return (
    <div className="sv2-card sv2-card-pad" style={{ marginTop: 10 }}>
      <div className="sv2-card-title">Portfolio intelligence</div>
      <div className="sv2-card-sub" style={{ marginBottom: 16 }}>Aggregate read across everything you hold</div>

      <div className="pv2-intel-grid">
        <div className="pv2-intel-card">
          <div className="dv2-stat-label">Aggregate Risk</div>
          <div className="pv2-intel-value">
            {intel.aggregateRiskScore != null ? (
              <>
                {intel.aggregateRiskScore}
                <span className="pv2-intel-unit">/100</span>
              </>
            ) : (
              "—"
            )}
          </div>
          <div className="dv2-stat-sub">Weighted volatility across positions</div>
        </div>

        <div className="pv2-intel-card">
          <div className="dv2-stat-label">Sentiment Exposure</div>
          <div className="pv2-intel-value">{formattedSentiment}</div>
          <div className="dv2-stat-sub">Average read on what you own</div>
        </div>

        <div className="pv2-intel-card">
          <div className="dv2-stat-label">Signal Mix</div>
          <div className="pv2-signal-row">
            {signalEntries.length > 0 ? (
              signalEntries.map(([signal, count]) => (
                <span key={signal} className={`pv2-signal-pill ${signal.toLowerCase()}`}>
                  {signal} <span className="pv2-signal-count">×{count}</span>
                </span>
              ))
            ) : (
              <span className="sv2-muted sv2-small">—</span>
            )}
          </div>
          <div className="dv2-stat-sub">Current AI suggestion per position</div>
        </div>
      </div>

      {suggestions.length > 0 && (
        <ul className="pv2-bullet-list">
          {suggestions.map((s, i) => (
            <li key={i} className="pv2-bullet-item">{s}</li>
          ))}
        </ul>
      )}
    </div>
  );
}