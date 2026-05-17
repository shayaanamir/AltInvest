import { useTheme } from "../../context/ThemeContext";
import { INSIGHTS } from "../../data/constants";
import { makeStyles } from "../../styles/makeStyles";

const IMPACT_COLOR = (impact, t) => ({
  positive: t.accentGreen,
  negative: t.accentRed,
  neutral:  t.accentBlue,
}[impact] ?? t.accentBlue);

function InsightItem({ source, time, headline, impact }) {
  const { tokens: t } = useTheme();
  const s = makeStyles(t);
  const color = IMPACT_COLOR(impact, t);

  return (
    <div style={s.insightItem}>
      <div style={s.insightMeta}>
        <span style={s.insightSrc}>{source}</span>
        <span style={s.insightTime}>{time}</span>
      </div>
      <div style={s.insightHL}>{headline}</div>
      <div style={{ display: "flex", alignItems: "center", gap: 5, marginTop: 4 }}>
        <span style={{ width: 6, height: 6, borderRadius: "50%", background: color, display: "inline-block" }} />
        <span style={{ fontSize: 10, color }}>{impact} impact</span>
      </div>
    </div>
  );
}

export default function InsightsPanel() {
  const { tokens: t } = useTheme();
  const s = makeStyles(t);

  return (
    <div style={s.card}>
      <div style={s.cardHeader}>
        <div style={{ display: "flex", alignItems: "center" }}>
          <span style={{ color: t.accentBlue, marginRight: 6, fontSize: 13 }}>✦</span>
          <span style={s.cardTitle}>AI Market Insights</span>
        </div>
        <button style={s.viewAllBtn}>View All</button>
      </div>

      <div style={{ display: "flex", flexDirection: "column" }}>
        {INSIGHTS.map((item) => (
          <InsightItem key={item.source + item.time} {...item} />
        ))}
      </div>
    </div>
  );
}
