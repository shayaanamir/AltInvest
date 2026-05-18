import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";

const ASSETS = [
    { rank: 1, sym: "BTC", bullish: 82, neutral: 10, bearish: 8, label: "Bullish", labelColor: "green" },
    { rank: 2, sym: "ETH", bullish: 48, neutral: 38, bearish: 14, label: "Neutral", labelColor: "neutral" },
    { rank: 3, sym: "SOL", bullish: 71, neutral: 17, bearish: 12, label: "Bullish", labelColor: "green" },
    { rank: 4, sym: "BAYC", bullish: 22, neutral: 18, bearish: 60, label: "Bearish", labelColor: "red" },
    { rank: 5, sym: "T-REX", bullish: 44, neutral: 42, bearish: 14, label: "Neutral", labelColor: "neutral" },
    { rank: 6, sym: "PAXG", bullish: 65, neutral: 22, bearish: 13, label: "Bullish", labelColor: "green" },
];

export default function AssetSentimentRanking() {
    const { tokens: t } = useTheme();
    const s = makeStyles(t);

    const labelColor = (c) => c === "green" ? t.accentGreen : c === "red" ? t.accentRed : t.textMuted;

    return (
        <div style={s.card}>
            <div style={s.cardHeader}>
                <span style={s.cardTitle}>Asset Sentiment Ranking</span>
            </div>
            <div>
                {ASSETS.map((a, i) => (
                    <div key={a.sym} style={{
                        display: "grid", gridTemplateColumns: "22px 56px 1fr 70px",
                        alignItems: "center", gap: 10,
                        padding: "11px 16px",
                        borderBottom: i < ASSETS.length - 1 ? `1px solid ${t.border}` : "none",
                    }}>
                        {/* Rank */}
                        <span style={{ fontSize: 11, color: t.textMuted, fontWeight: 600 }}>{a.rank}</span>

                        {/* Symbol */}
                        <span style={{ fontSize: 12.5, fontWeight: 700, color: t.textPrimary }}>{a.sym}</span>

                        {/* Bar */}
                        <div style={{ height: 7, borderRadius: 4, overflow: "hidden", background: t.bgCard2, display: "flex" }}>
                            <div style={{ width: `${a.bullish}%`, background: t.accentGreen, transition: "width 0.5s" }} />
                            <div style={{ width: `${a.neutral}%`, background: t.borderLight }} />
                            <div style={{ width: `${a.bearish}%`, background: t.accentRed }} />
                        </div>

                        {/* Label */}
                        <span style={{ fontSize: 11, fontWeight: 700, color: labelColor(a.labelColor), textAlign: "right" }}>
                            {a.label}
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
}