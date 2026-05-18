import { useState, useEffect } from "react";
import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";
import { sentimentApi } from "../../services/sentimentApi";

export default function SentimentHeadlines() {
    const { tokens: t } = useTheme();
    const s = makeStyles(t);

    const [headlines, setHeadlines] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        sentimentApi.getTopHeadlines().then(data => {
            setHeadlines(data);
            setLoading(false);
        }).catch(console.error);
    }, []);

    const getScoreStyle = (score) => {
        if (score > 0.5) return { color: t.accentGreen, bg: "rgba(0,212,139,0.12)" };
        if (score < -0.5) return { color: t.accentRed, bg: "rgba(255,64,96,0.12)" };
        return { color: t.textSecondary, bg: t.bgCard2 };
    };

    return (
        <div style={{ ...s.card, marginTop: 10 }}>
            <div style={s.cardHeader}>
                <span style={s.cardTitle}>Global Top Headlines</span>
                <span style={{ fontSize: 10, color: t.textMuted }}>Recent AI-Analyzed Articles</span>
            </div>

            {loading ? (
                <div style={{ padding: "30px 14px", color: t.textMuted, fontSize: 13, textAlign: "center" }}>
                    Loading global headlines...
                </div>
            ) : headlines.length === 0 ? (
                <div style={{ padding: "30px 14px", color: t.textMuted, fontSize: 13, textAlign: "center" }}>
                    No headlines available.
                </div>
            ) : (
                <div style={{ display: "flex", flexDirection: "column" }}>
                    {headlines.map((item, i) => {
                        const style = getScoreStyle(item.score);
                        return (
                            <div key={i} style={{
                                padding: "16px",
                                borderBottom: i < headlines.length - 1 ? `1px solid ${t.border}` : "none",
                                display: "flex",
                                gap: 14,
                            }}>
                                <div style={{
                                    minWidth: 44, height: 44, borderRadius: 8,
                                    background: style.bg, color: style.color,
                                    display: "flex", alignItems: "center", justifyContent: "center",
                                    fontSize: 12, fontWeight: 700,
                                    border: `1px solid ${style.color}44`
                                }}>
                                    {item.score > 0 ? "+" : ""}{(item.score * 100).toFixed(0)}
                                </div>
                                <div style={{ flex: 1 }}>
                                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
                                        <a href={item.link} target="_blank" rel="noreferrer" style={{ 
                                            fontSize: 14, 
                                            fontWeight: 600, 
                                            color: t.textPrimary,
                                            textDecoration: "none",
                                            lineHeight: 1.4
                                        }}>
                                            {item.title}
                                        </a>
                                    </div>
                                    <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 11, color: t.textMuted, fontWeight: 500 }}>
                                        <span style={{ 
                                            color: t.accentBlue, 
                                            background: "rgba(0,163,255,0.1)", 
                                            padding: "2px 6px", 
                                            borderRadius: 4,
                                            textTransform: "uppercase" 
                                        }}>
                                            {item.asset_id}
                                        </span>
                                        <span>•</span>
                                        <span>{item.source}</span>
                                        <span>•</span>
                                        <span>{item.age_hours}h ago</span>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
