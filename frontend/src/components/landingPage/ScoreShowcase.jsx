import assetsData from "../../data/sample_data/assets.json";

function deriveSignal(score) {
  if (score >= 75) return { label: "Strong Buy", tone: "positive" };
  if (score >= 55) return { label: "Buy", tone: "positive" };
  if (score >= 45) return { label: "Hold", tone: "neutral" };
  if (score >= 25) return { label: "Sell", tone: "negative" };
  return { label: "Strong Sell", tone: "negative" };
}

// Same low/medium/high banding used on the asset detail Risk Overview
// card (RiskAnalytics.jsx) — low is good, high is bad, unless the
// metric itself is "higher = better" (liquidity), in which case invert it.
function riskTone(value, higherIsBetter = false) {
  if (higherIsBetter) {
    if (value >= 80) return "low";
    if (value >= 40) return "medium";
    return "high";
  }
  if (value >= 60) return "high";
  if (value >= 30) return "medium";
  return "low";
}

const TONE_VAR = {
  low: "var(--sv2-green)",
  medium: "var(--sv2-accent)",
  high: "var(--sv2-red)",
};

const BULLETS = [
  "Composite AAI score with confidence and meaning label",
  "Sentiment with distribution, drivers and source breakdown",
  "Risk split into volatility, liquidity, regulatory and market",
  "Your holdings and watchlists shown as context everywhere",
];

export default function ScoreShowcase() {
  const asset = assetsData.assets[0]; // Bitcoin
  const { label, tone } = deriveSignal(asset.aai.score);

  const metrics = [
    { label: "Volatility Index", value: asset.risk.volatilityIndex, tone: riskTone(asset.risk.volatilityIndex) },
    { label: "Liquidity Score", value: asset.risk.liquidityScore, tone: riskTone(asset.risk.liquidityScore, true) },
    { label: "Regulatory Risk", value: asset.risk.regulatoryRisk, tone: riskTone(asset.risk.regulatoryRisk) },
    { label: "Market Risk", value: asset.risk.marketRisk, tone: riskTone(asset.risk.marketRisk) },
  ];

  return (
    <section className="lp2-section">
      <div className="lp2-section-inner lp2-analytics-grid">
        <div>
          <div className="lp2-eyebrow">Analytics</div>
          <h2 className="lp2-heading" style={{ marginBottom: 20 }}>
            Scores you can interrogate, not just accept.
          </h2>
          <p className="lp2-body-text">
            Every AAI score, sentiment read and risk band carries its confidence and
            its evidence base. When a signal rests on thin sourcing, the interface
            says so instead of rounding it into certainty.
          </p>
          <ul className="lp2-bullet-list">
            {BULLETS.map((b) => (
              <li key={b}>{b}</li>
            ))}
          </ul>
        </div>

        <div className="lp2-score-card">
          <div className="lp2-score-eyebrow">Alternative Asset Index — {asset.name}</div>

          <div className="lp2-score-signal-row">
            <span className="lp2-score-big">{Math.round(asset.aai.score)}</span>
            <span>
              <span className={`lp2-signal-tag ${tone}`}>{label.toUpperCase()}</span>
              <div className="lp2-score-confidence">{Math.round(asset.aai.confidence * 100)}% confidence</div>
            </span>
          </div>

          <div className="lp2-metrics">
            {metrics.map((m) => (
              <div className="lp2-metric-row" key={m.label}>
                <div className="lp2-metric-label-row">
                  <span>{m.label}</span>
                  <span>{m.value}</span>
                </div>
                <div className="lp2-metric-track">
                  <div className="lp2-metric-fill" style={{ width: `${m.value}%`, background: TONE_VAR[m.tone] }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}