import { useState, useEffect } from "react";
import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";
import { dashboardApi } from "../../services/dashboardApi";

function StatCard({ label, value, change, positive }) {
  const { tokens: t } = useTheme();
  const s = makeStyles(t);
  const badgeBg    = positive ? t.tagGreenBg : t.tagRedBg;
  const badgeColor = positive ? t.accentGreen : t.accentRed;

  return (
    <div style={s.statCard}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <div style={{ ...s.statLabel, marginBottom: 0 }}>{label}</div>
        <span style={{ ...s.statBadge, background: badgeBg, color: badgeColor, marginBottom: 0 }}>{change}</span>
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
      label: "Total Portfolio Value", 
      value: "$" + stats.totalPortfolioValue.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 }), 
      change: stats.portfolioChange, 
      positive: stats.portfolioPositive 
    },
    { 
      label: "24h Volume (Alt)",      
      value: "$" + (stats.totalVolume24h / 1e9).toFixed(2) + "B",  
      change: stats.volumeChange,  
      positive: stats.volumePositive 
    },
    { 
      label: "Global AAI Sentiment",  
      value: stats.globalSentiment + "/100",
      change: stats.sentimentChange,  
      positive: stats.sentimentPositive 
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
