import { useState, useEffect } from "react";
import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";
import { dashboardApi } from "../../services/dashboardApi";

const UpArrow = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="currentColor" className="bi bi-arrow-up-right" viewBox="0 0 16 16" style={{ marginRight: 4, display: "inline" }}>
    <path fillRule="evenodd" d="M14 2.5a.5.5 0 0 0-.5-.5h-6a.5.5 0 0 0 0 1h4.793L2.146 13.146a.5.5 0 0 0 .708.708L13 3.707V8.5a.5.5 0 0 0 1 0z" />
  </svg>
);

const DownArrow = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="currentColor" className="bi bi-arrow-down-left" viewBox="0 0 16 16" style={{ marginRight: 4, display: "inline" }}>
    <path fillRule="evenodd" d="M2 13.5a.5.5 0 0 0 .5.5h6a.5.5 0 0 0 0-1H3.707L13.854 2.854a.5.5 0 0 0-.708-.708L3 12.293V7.5a.5.5 0 0 0-1 0z" />
  </svg>
);

function StatCard({ label, value, change, Positive }) {
  const { tokens: t } = useTheme();
  const s = makeStyles(t);
  const badgeBg = Positive ? t.tagGreenBg : t.tagRedBg;
  const badgeColor = Positive ? t.accentGreen : t.accentRed;

  return (
    <div style={s.statCard}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <div style={{ ...s.statLabel, marginBottom: 0 }}>{label}</div>
        <span style={{ ...s.statBadge, background: badgeBg, color: badgeColor, marginBottom: 0, display: "flex", alignItems: "center" }}>
          {Positive ? <UpArrow /> : <DownArrow />}
          {change}
        </span>
      </div>
      <div style={s.statValue}>{value}</div>
    </div>
  );
}

function MoodCard({ mood, confidence }) {
  const { tokens: t } = useTheme();
  const s = makeStyles(t);

  const isBullish = mood === "bullish";
  const isBearish = mood === "bearish";
  const color = isBullish ? t.accentGreen : isBearish ? t.accentRed : t.textMuted;
  const label = isBullish ? "Bullish ↗" : isBearish ? "Bearish ↘" : "Neutral ⟷";

  return (
    <div style={s.statCard}>
      <div style={s.moodLabel}>Market Mood</div>
      <div style={s.moodValue}>
        <span style={{ color, fontWeight: 700, fontSize: 20 }}>{label}</span>
        <div style={s.moodSquare} />
      </div>
      <div style={s.moodConf}>AI confidence: {confidence}%</div>
    </div>
  );
}

export default function StatsRow() {
  const { tokens: t } = useTheme();
  const s = makeStyles(t);

  const [stats, setStats] = useState(null);

  useEffect(() => {
    dashboardApi.getStats().then(setStats).catch(console.error);
  }, []);

  if (!stats) {
    return <div style={{ ...s.statsRow, opacity: 0.5 }}>Loading stats...</div>;
  }

  const statItems = [
    {
      label: "Portfolio Value",
      value: "$" + stats.totalPortfolioValue.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 }),
      change: stats.portfolioChange,
      Positive: stats.portfolioPositive
    },
    {
      label: "Market Volume",
      value: "$" + (stats.totalVolume24h / 1e9).toFixed(2) + "B",
      change: stats.volumeChange,
      Positive: stats.volumePositive
    },
    {
      label: "Market Sentiment",
      value: stats.globalSentiment + "/100",
      change: stats.sentimentChange,
      Positive: stats.sentimentPositive
    },
  ];

  return (
    <div style={s.statsRow}>
      {statItems.map((stat) => (
        <StatCard key={stat.label} {...stat} />
      ))}
      <MoodCard mood={stats.marketMood} confidence={84} />
    </div>
  );
}
