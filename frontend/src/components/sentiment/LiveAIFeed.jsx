import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";

const FEED = [
    {
        handle: "@crypto_whale",
        platform: "Twitter",
        time: "10m ago",
        text: "Massive accumulation happening on $BTC right now. Institutional flows are undeniable.",
        signal: "Positive Signal",
        signalType: "Positive",
    },
    {
        handle: "u/investor_pro",
        platform: "Reddit",
        time: "45m ago",
        text: "The regulatory clarity around tokenized real estate is finally improving. Bullish on RWA index.",
        signal: "Positive Signal",
        signalType: "Positive",
    },
    {
        handle: "@nft_degen",
        platform: "Twitter",
        time: "1h ago",
        text: "Floor prices are dropping again. Liquidity is completely drying up in the mid-tier collections.",
        signal: "Negative Signal",
        signalType: "Negative",
    },
    {
        handle: "Bloomberg",
        platform: "News",
        time: "2h ago",
        text: "Commodities rally as inflation data comes in hotter than expected.",
        signal: "Neutral Signal",
        signalType: "neutral",
    },
];

const PLATFORM_COLORS = {
    Twitter: "#1d9bf0",
    Reddit: "#ff4500",
    News: "#f5b731",
};

export default function LiveAIFeed() {
    const { tokens: t } = useTheme();
    const s = makeStyles(t);

    const signalStyle = (type) => {
        if (type === "Positive") return { background: "rgba(0,212,139,0.12)", color: t.accentGreen, border: `1px solid ${t.accentGreen}44` };
        if (type === "Negative") return { background: "rgba(255,64,96,0.12)", color: t.accentRed, border: `1px solid ${t.accentRed}44` };
        return { background: t.bgCard2, color: t.textMuted, border: `1px solid ${t.borderLight}` };
    };

    const signalIcon = (type) =>
        type === "Positive" ? "✦" : type === "Negative" ? "✦" : "◆";

    return (
        <div style={s.card}>
            <div style={s.cardHeader}>
                <span style={s.cardTitle}>Live AI Feed</span>
                <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
                    <span style={{
                        width: 7, height: 7, borderRadius: "50%",
                        background: t.accentGreen,
                        boxShadow: `0 0 6px ${t.accentGreen}`,
                        display: "inline-block",
                        animation: "none",
                    }} />
                    <span style={{ fontSize: 10.5, color: t.accentGreen, fontWeight: 600 }}>Live</span>
                </span>
            </div>

            <div style={{ overflow: "auto", maxHeight: 420 }}>
                {FEED.map((item, i) => (
                    <div key={i} style={{
                        padding: "13px 15px",
                        borderBottom: i < FEED.length - 1 ? `1px solid ${t.border}` : "none",
                    }}>
                        {/* Top row */}
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                                <span style={{ fontSize: 12, fontWeight: 700, color: t.textPrimary }}>{item.handle}</span>
                                <span style={{
                                    fontSize: 9, fontWeight: 700, padding: "1px 7px", borderRadius: 4,
                                    background: `${PLATFORM_COLORS[item.platform]}22`,
                                    color: PLATFORM_COLORS[item.platform],
                                    border: `1px solid ${PLATFORM_COLORS[item.platform]}44`,
                                }}>
                                    {item.platform}
                                </span>
                            </div>
                            <span style={{ fontSize: 9.5, color: t.textMuted }}>{item.time}</span>
                        </div>

                        {/* Text */}
                        <p style={{ fontSize: 11.5, color: t.textSecondary, lineHeight: 1.55, margin: "0 0 8px" }}>
                            {item.text}
                        </p>

                        {/* Signal tag */}
                        <span style={{
                            ...signalStyle(item.signalType),
                            display: "inline-flex", alignItems: "center", gap: 5,
                            fontSize: 10, fontWeight: 700, padding: "3px 10px", borderRadius: 5,
                        }}>
                            <span style={{ fontSize: 8 }}>{signalIcon(item.signalType)}</span>
                            {item.signal}
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
}