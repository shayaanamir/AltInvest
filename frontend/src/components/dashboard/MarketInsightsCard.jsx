import { useNavigate } from "react-router-dom";
import { useAsync } from "../../hooks/useAsync";
import { dashboardApi } from "../../services/dashboardApi";
import { timeAgo } from "../../utils/dateTime";

export default function MarketInsightsCard() {
  const { data: insights } = useAsync(() => dashboardApi.getMarketInsights(), []);
  const navigate = useNavigate();

  return (
    <div className="sv2-card sv2-card-pad" style={{ display: "flex", flexDirection: "column" }}>
      <div>
        <div className="sv2-card-title">Market insights</div>
        <div className="sv2-card-sub">What's moving the numbers</div>
      </div>

      <div style={{ marginTop: 10, overflowY: "auto", maxHeight: 300 }}>
        {!insights ? (
          <div className="sv2-muted sv2-small" style={{ padding: "16px 0" }}>Loading…</div>
        ) : insights.length === 0 ? (
          <div className="sv2-muted sv2-small" style={{ padding: "16px 0" }}>No market insights right now.</div>
        ) : (
          insights.map((item) => (
            <div key={item.id} className="dv2-insight-item">
              <div className="dv2-insight-meta">
                <span className="dv2-insight-src">{item.source} · {timeAgo(item.publishedAt)}</span>
                <span className={`dv2-insight-badge ${item.impact === "Positive" ? "positive" : item.impact === "Negative" ? "negative" : ""}`}>
                  {item.impact}
                </span>
              </div>
              <p className="dv2-insight-title">{item.title}</p>
              <div className="dv2-insight-links">
                <span className="dv2-insight-link" title="No source URL in this insight's data">
                  Read source ↗
                </span>
                {item.relatedAssetSymbol && (
                  <button type="button" className="dv2-insight-link" onClick={() => navigate("/asset-detail")}>
                    Open asset →
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}