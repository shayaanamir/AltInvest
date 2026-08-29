import assetsData from "../../data/sample_data/assets.json";
import { getAaiSignal, getRiskTone } from "../../utils/scoring";

const TONE_VAR = {
  positive: "var(--sv2-green)",
  neutral: "var(--sv2-accent)",
  negative: "var(--sv2-red)",
};

const BULLETS = [
  "Composite AAI score with confidence and meaning label",
  "Sentiment with distribution, drivers and source breakdown",
  "Risk split into volatility, liquidity, regulatory and market",
  "Your holdings and watchlists shown as context everywhere",
];

export default function ScoreShowcase() {
  const asset = assetsData.assets[0]; // Bitcoin
  const { label, tone } = getAaiSignal(asset.aai.score);

  const metrics = [
    { label: "Volatility Index", value: asset.risk.volatilityIndex, tone: getRiskTone(asset.risk.volatilityIndex) },
    { label: "Liquidity Score", value: asset.risk.liquidityScore, tone: getRiskTone(asset.risk.liquidityScore, { higherIsBetter: true }) },
    { label: "Regulatory Risk", value: asset.risk.regulatoryRisk, tone: getRiskTone(asset.risk.regulatoryRisk) },
    { label: "Market Risk", value: asset.risk.marketRisk, tone: getRiskTone(asset.risk.marketRisk) },
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