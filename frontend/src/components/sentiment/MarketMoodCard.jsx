import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";

export default function MarketMoodCard() {
    const { tokens: t } = useTheme();
    const s = makeStyles(t);

    // Greed = ~75% along the bar
    const greedPct = 75;

    return (
        <div style={s.card}>
            <div style={{ padding: "16px 16px 18px", display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
                <span style={{ fontSize: 10.5, color: t.textMuted, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase" }}>
                    Current Market Mood
                </span>
                <span style={{
                    fontSize: 34, fontWeight: 800,
                    color: t.accentGreen,
                    letterSpacing: "-1px",
                    lineHeight: 1.1,
                    marginTop: 2,
                }}>
                    Greed
                </span>

                {/* Fear → Greed gradient bar */}
                <div style={{ width: "100%", marginTop: 10 }}>
                    <div style={{
                        width: "100%", height: 8, borderRadius: 6,
                        background: `linear-gradient(to right, #ff4060, #f5b731, #00d48b)`,
                        position: "relative",
                    }}>
                        {/* Needle */}
                        <div style={{
                            position: "absolute",
                            top: "50%", left: `${greedPct}%`,
                            transform: "translate(-50%, -50%)",
                            width: 14, height: 14, borderRadius: "50%",
                            background: "#fff",
                            border: `2px solid ${t.accentGreen}`,
                            boxShadow: `0 0 6px ${t.accentGreen}88`,
                        }} />
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", marginTop: 5 }}>
                        <span style={{ fontSize: 9.5, color: t.textMuted }}>Fear</span>
                        <span style={{ fontSize: 9.5, color: t.textMuted }}>Greed</span>
                    </div>
                </div>
            </div>
        </div>
    );
}