import { useNavigate } from "react-router-dom";
import { confidenceLabel } from "../../services/assetDetailApi";

export default function SentimentReadCard({ sentimentSnippet }) {
  const navigate = useNavigate();
  if (!sentimentSnippet) return null;

  const { score, label, confidence } = sentimentSnippet;
  const tone = score > 0.1 ? "positive" : score < -0.1 ? "negative" : "neutral";
  const formatted = (score >= 0 ? "+" : "") + score.toFixed(2);

  return (
    <div className="sv2-card adt-panel-card">
      <div className="adt-panel-label">Sentiment Read</div>
      <div className={`adt-sentiment-score ${tone}`}>{formatted}</div>
      <div className={`adt-sentiment-label ${tone}`}>{label}</div>

      <div className="sv2-bipolar-progress-container adt-mt-14">
        <div className="sv2-bipolar-track">
          <div
            className="sv2-bipolar-fill"
            style={{
              left: score >= 0 ? "50%" : `${50 + score * 50}%`,
              width: `${Math.abs(score) * 50}%`,
              background:
                tone === "positive" ? "var(--sv2-green)" :
                tone === "negative" ? "var(--sv2-red)" : "var(--sv2-text-mute)",
            }}
          />
        </div>
      </div>

      <div className="adt-panel-sub adt-mt-10">
        {confidence}% confidence · {confidenceLabel(confidence)}
      </div>

      <button className="adt-see-sentiment-link" onClick={() => navigate("/sentiment")}>
        See full sentiment →
      </button>
    </div>
  );
}