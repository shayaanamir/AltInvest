import { sentimentReadLabel, evidenceLabel } from "../../services/compareApi";

export default function CompareSentimentTable({ assets }) {
  return (
    <div className="cmp-card cmp-sentiment-card">
      <div className="cmp-chart-title">Sentiment</div>
      <div className="cmp-chart-sub">Score, confidence and direction per asset</div>

      <div className="cmp-sent-table">
        <div className="cmp-sent-row cmp-sent-head">
          <span>Asset</span>
          <span>Score</span>
          <span>Read</span>
          <span>Confidence</span>
          <span>Evidence</span>
          <span>24h trend</span>
        </div>
        {assets.map((a) => {
          const trendUp = a.sentimentTrend === "rising" || a.sentimentTrend === "improving";
          const trendDown = a.sentimentTrend === "falling" || a.sentimentTrend === "deteriorating";
          const trendPct = Math.round(Math.abs(a.sentimentScore * a.sentimentConfidence * 40) * 100) / 100;

          return (
            <div key={a.id} className="cmp-sent-row">
              <span className="cmp-sent-name">{a.name}</span>
              <span>
                {a.sentimentScore >= 0 ? "+" : ""}
                {a.sentimentScore.toFixed(2)}
              </span>
              <span>{sentimentReadLabel(a.sentimentScore)}</span>
              <span>{Math.round(a.sentimentConfidence * 100)}%</span>
              <span className="cmp-sent-evidence">{evidenceLabel(a.sentimentConfidenceLabel)}</span>
              <span>
                <span className={`cmp-trend-badge ${trendDown ? "negative" : trendUp ? "positive" : "neutral"}`}>
                  {trendDown ? "↘" : "↗"} +{trendPct.toFixed(2)}%
                </span>
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}