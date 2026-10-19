import { useAsync } from "../../hooks/useAsync";
import { assetDetailApi } from "../../services/assetDetailApi";
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

// The card is a live example: it shows Bitcoin's current score and risk breakdown from the API.
// If the API isn't reachable or has no score for it, the card says so instead of showing numbers.
const EXAMPLE_SYMBOL = "BTC";

export default function ScoreShowcase() {
  const { data: asset, loading } = useAsync(() => assetDetailApi.getAssetDetail(EXAMPLE_SYMBOL), []);
  const score = asset?.aaiPanel?.score;
  const { label, tone } = score != null ? getAaiSignal(score) : { label: "", tone: "neutral" };

  const metrics = (asset?.riskOverview || []).map((r) => ({
    label: r.label,
    value: r.value,
    tone: getRiskTone(r.value, { higherIsBetter: r.label === "Liquidity Score" }),
  }));

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
          <div className="lp2-score-eyebrow">Alternative Asset Index — {asset?.header?.name || EXAMPLE_SYMBOL}</div>

          {score == null ? (
            <div className="lp2-score-confidence">
              {loading ? "Loading a live example…" : "A live example isn't available right now."}
            </div>
          ) : (
            <div className="lp2-score-signal-row">
              <span className="lp2-score-big">{Math.round(score)}</span>
              <span>
                <span className={`lp2-signal-tag ${tone}`}>{label.toUpperCase()}</span>
                {asset.aaiPanel.confidence != null && (
                  <div className="lp2-score-confidence">{Math.round(asset.aaiPanel.confidence * 100)}% confidence</div>
                )}
              </span>
            </div>
          )}

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