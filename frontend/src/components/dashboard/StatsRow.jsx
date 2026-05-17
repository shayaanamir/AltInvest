import { useTheme } from "../../context/ThemeContext";
import { STATS } from "../../data/constants";
import { makeStyles } from "../../styles/makeStyles";

function StatCard({ label, value, change, positive }) {
  const { tokens: t } = useTheme();
  const s = makeStyles(t);
  const badgeBg    = positive ? t.tagGreenBg : t.tagRedBg;
  const badgeColor = positive ? t.accentGreen : t.accentRed;

  return (
    <div style={s.statCard}>
      <div style={s.statLabel}>{label}</div>
      <span style={{ ...s.statBadge, background: badgeBg, color: badgeColor }}>{change}</span>
      <div style={s.statValue}>{value}</div>
    </div>
  );
}

function MoodCard() {
  const { tokens: t } = useTheme();
  const s = makeStyles(t);

  return (
    <div style={s.statCard}>
      <div style={s.moodLabel}>Market Mood</div>
      <div style={s.moodValue}>
        <span style={{ color: t.accentGreen, fontWeight: 700, fontSize: 20 }}>Bullish ↗</span>
        <div style={s.moodSquare} />
      </div>
      <div style={s.moodConf}>AI confidence: 84%</div>
    </div>
  );
}

export default function StatsRow() {
  const { tokens: t } = useTheme();
  const s = makeStyles(t);

  return (
    <div style={s.statsRow}>
      {STATS.map((stat) => (
        <StatCard key={stat.label} {...stat} />
      ))}
      <MoodCard />
    </div>
  );
}
