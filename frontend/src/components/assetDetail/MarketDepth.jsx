import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";

const STATS = [
    { label: "Market Cap", value: "$1.24T" },
    { label: "24h Volume", value: "$32.5B" },
    { label: "Circulating Supply", value: "19.6M BTC" },
    { label: "All Time High", value: "$73,750" },
];

export default function MarketDepth() {
    const { tokens: t } = useTheme();
    const s = makeStyles(t);

    return (
        <div style={s.card}>
            <div style={{ padding: "11px 14px 10px", borderBottom: `1px solid ${t.border}` }}>
                <span style={{ ...s.cardTitle, display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ fontSize: 14, color: t.accentBlue }}>↯</span> Market Depth &amp; Stats
                </span>
            </div>
            <div style={{
                display: "grid", gridTemplateColumns: "repeat(4, 1fr)",
            }}>
                {STATS.map((stat, i) => (
                    <div key={stat.label} style={{
                        padding: "12px 16px",
                        borderRight: i < STATS.length - 1 ? `1px solid ${t.border}` : "none",
                    }}>
                        <div style={{ fontSize: 10, color: t.textMuted, fontWeight: 500, marginBottom: 5 }}>{stat.label}</div>
                        <div style={{ fontSize: 13.5, fontWeight: 700, color: t.textPrimary }}>{stat.value}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}