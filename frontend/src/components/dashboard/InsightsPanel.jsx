import { useState, useEffect } from "react";
import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";
import { dashboardApi } from "../../services/dashboardApi";

const IMPACT_COLOR = (impact, t) => ({
  Positive: t.accentGreen,
  Negative: t.accentRed,
  neutral: t.accentBlue,
}[impact] ?? t.accentBlue);

function timeAgo(dateString) {
  const diff = (new Date() - new Date(dateString)) / 1000 / 60;
  if (diff < 0) return "just now";
  if (diff < 60) return `${Math.floor(diff)}m ago`;
  const hours = Math.floor(diff / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function InsightItem({ source, published_at, title, impact }) {
  const { tokens: t } = useTheme();
  const s = makeStyles(t);
  const color = IMPACT_COLOR(impact, t);
  const time = timeAgo(published_at);

  return (
    <div style={s.insightItem}>
      <div style={s.insightMeta}>
        <span style={s.insightSrc}>{source}</span>
        <span style={s.insightTime}>{time}</span>
      </div>
      <div style={s.insightHL}>{title}</div>
      <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
        <span style={{ width: 6, height: 6, borderRadius: "50%", background: color, display: "inline-block" }} />
        <span style={{ fontSize: 10, color }}>{impact} Impact</span>
      </div>
    </div>
  );
}

export default function InsightsPanel() {
  const { tokens: t } = useTheme();
  const s = makeStyles(t);

  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dashboardApi.getMarketInsights().then(res => {
      setInsights(res);
      setLoading(false);
    }).catch(console.error);
  }, []);

  return (
    <div style={s.card}>
      <div style={s.cardHeader}>
        <div style={{ display: "flex", alignItems: "center" }}>
          <span style={s.cardTitle}>Market Insights</span>
        </div>
        {/* <button style={s.viewAllBtn}>View All</button> */}
      </div>

      <div style={{ display: "flex", flexDirection: "column", maxHeight: 270, overflowY: "auto", overflowX: "hidden" }}>
        {loading ? (
          <div style={{ padding: "14px", color: t.textMuted, fontSize: 12 }}>Loading insights...</div>
        ) : (
          insights.map((item) => (
            <InsightItem key={item.id} {...item} />
          ))
        )}
      </div>
    </div>
  );
}
