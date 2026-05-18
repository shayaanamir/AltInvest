import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";

const TOPICS = [
    "#BitcoinETF", "#RWAs", "#FedRate", "#SolanaSummer",
    "#NFTMarket", "#DeFi",
];

export default function TrendingTopics() {
    const { tokens: t } = useTheme();
    const s = makeStyles(t);

    return (
        <div style={s.card}>
            <div style={{ padding: "11px 14px 10px", borderBottom: `1px solid ${t.border}` }}>
                <span style={{ ...s.cardTitle, display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ color: t.accentBlue, fontSize: 14 }}>#</span> Trending Topics
                </span>
            </div>
            <div style={{ padding: "12px 14px", display: "flex", flexWrap: "wrap", gap: 7 }}>
                {TOPICS.map(topic => (
                    <div key={topic} style={{
                        display: "flex", alignItems: "center", gap: 5,
                        background: t.bgCard2, border: `1px solid ${t.borderLight}`,
                        borderRadius: 20, padding: "5px 11px",
                        fontSize: 11, fontWeight: 600, color: t.textSecondary,
                        cursor: "pointer",
                    }}>
                        {topic}
                        <span style={{
                            width: 5, height: 5, borderRadius: "50%",
                            background: t.accentGreen, display: "inline-block", flexShrink: 0,
                        }} />
                    </div>
                ))}
            </div>
        </div>
    );
}