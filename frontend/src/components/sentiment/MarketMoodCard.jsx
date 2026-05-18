import { useState, useEffect } from "react";
import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";
import { sentimentApi } from "../../services/sentimentApi";

export default function MarketMoodCard() {
    const { tokens: t } = useTheme();
    const s = makeStyles(t);

    const [score, setScore] = useState(0.5); // Default to 0.5 (Neutral)
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        sentimentApi.getSentimentData().then(data => {
            setScore(data.globalScore);
            setLoading(false);
        }).catch(console.error);
    }, []);

    let mood = "Neutral";
    let color = t.accentYellow;

    if (score <= 0.45) {
        mood = "Bearish";
        color = t.accentRed;
    } else if (score >= 0.55) {
        mood = "Bullish";
        color = t.accentGreen;
    }

    const needlePct = score * 100;

    return (
        <div style={s.card}>
            <div style={{ padding: "16px 16px 18px", display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
                <span style={{ fontSize: 10.5, color: t.textMuted, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase" }}>
                    Sentiment Score
                </span>

                {loading ? (
                    <span style={{ fontSize: 24, fontWeight: 600, color: t.textMuted, marginTop: 2, height: 38, display: "flex", alignItems: "center" }}>
                        ...
                    </span>
                ) : (
                    <span style={{
                        fontSize: 34, fontWeight: 800,
                        color: color,
                        letterSpacing: "-1px",
                        lineHeight: 1.1,
                        marginTop: 2,
                        textTransform: "capitalize"
                    }}>
                        {mood}
                    </span>
                )}

                {/* Bearish → Bullish gradient bar */}
                <div style={{ width: "100%", marginTop: 10 }}>
                    <div style={{
                        width: "100%", height: 8, borderRadius: 6,
                        background: `linear-gradient(to right, #ff4060, #f5b731, #00d48b)`,
                        position: "relative",
                    }}>
                        {/* Needle */}
                        <div style={{
                            position: "absolute",
                            top: "50%", left: `${needlePct}%`,
                            transform: "translate(-50%, -50%)",
                            width: 14, height: 14, borderRadius: "50%",
                            background: "#fff",
                            border: `2px solid ${color}`,
                            boxShadow: `0 0 6px ${color}88`,
                            transition: "left 1s ease-out, border-color 1s, box-shadow 1s"
                        }} />
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", marginTop: 5 }}>
                        <span style={{ fontSize: 9.5, color: t.textMuted, width: 40 }}>Bearish</span>
                        <span style={{ fontSize: 11, color: t.textPrimary, fontWeight: 700, marginTop: '8px' }}>
                            {loading ? "" : (score).toFixed(2)}
                        </span>
                        <span style={{ fontSize: 9.5, color: t.textMuted, width: 40, textAlign: "right" }}>Bullish</span>
                        {/* <span style={{ fontSize: 9.5, color: t.textMuted, width: 40, textAlign: "right" }}>Sentiment Score</span> */}

                    </div>
                </div>
            </div>
        </div>
    );
}