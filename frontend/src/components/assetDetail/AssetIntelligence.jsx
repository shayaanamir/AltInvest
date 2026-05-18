import { useState, useEffect } from "react";
import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";
import { assetApi } from "../../services/assetApi";

export default function AssetIntelligence({ assetId = 101 }) {
    const { tokens: t } = useTheme();
    const s = makeStyles(t);

    const [data, setData] = useState({ score: 0, confidence: 0 });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        assetApi.getAssetIntelligence(assetId).then(res => {
            setData(res);
            setLoading(false);
        }).catch(console.error);
    }, [assetId]);

    let meaning = "NEUTRAL";
    let color = t.textMuted;

    if (data.score >= 0.6) {
        meaning = "STRONG BUY";
        color = t.accentGreen;
    } else if (data.score >= 0.2) {
        meaning = "BUY";
        color = t.accentGreen;
    } else if (data.score <= -0.6) {
        meaning = "STRONG SELL";
        color = t.accentRed;
    } else if (data.score <= -0.2) {
        meaning = "SELL";
        color = t.accentRed;
    }

    if (loading) {
        return (
            <div style={s.card}>
                <div style={{ padding: "12px 14px 10px", borderBottom: `1px solid ${t.border}` }}>
                    <span style={s.cardTitle}>Alternative Asset Index Score</span>
                </div>
                <div style={{ padding: "24px 14px", color: t.textMuted, fontSize: 13, textAlign: "center" }}>
                    Loading intelligence...
                </div>
            </div>
        );
    }

    const formattedScore = (data.score > 0 ? "+" : "") + (data.score);

    return (
        <div style={s.card}>
            <div style={{ padding: "12px 14px 10px", borderBottom: `1px solid ${t.border}` }}>
                <span style={s.cardTitle}>Alternative Asset Index Score</span>
            </div>

            {/* Large Score Display */}
            <div style={{
                display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
                padding: "36px 14px", gap: 4, height: 114
            }}>
                <div style={{ fontSize: 48, fontWeight: 800, color: t.textPrimary, letterSpacing: "-0.02em", lineHeight: 1, marginBottom: '10px' }}>
                    {formattedScore}
                </div>
                <div style={{ fontSize: 12, color: t.accentBlue, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    AAI Score
                </div>
            </div>

            {/* Bottom metrics */}
            <div style={{
                display: "grid", gridTemplateColumns: "1fr 1fr",
                borderTop: `1px solid ${t.border}`,
            }}>
                <div style={{ padding: "12px 14px", borderRight: `1px solid ${t.border}` }}>
                    <div style={{ fontSize: 9.5, color: t.textMuted, fontWeight: 600, marginBottom: 6 }}>Meaning</div>
                    <div style={{ fontSize: 14, fontWeight: 800, color: color, letterSpacing: "0.01em", lineHeight: 1.2 }}>
                        {meaning.split(" ").map((word, i) => (
                            <div key={i}>{word}</div>
                        ))}
                    </div>
                </div>
                <div style={{ padding: "12px 14px" }}>
                    <div style={{ fontSize: 9.5, color: t.textMuted, fontWeight: 600, marginBottom: 6 }}>Confidence</div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: t.textPrimary }}>{data.confidence}%</div>
                </div>
            </div>
        </div>
    );
}