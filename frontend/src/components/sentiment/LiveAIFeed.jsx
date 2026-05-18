import { useState, useEffect } from "react";
import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";
import { sentimentApi } from "../../services/sentimentApi";

export default function SentimentSources() {
    const { tokens: t } = useTheme();
    const s = makeStyles(t);

    const [breakdown, setBreakdown] = useState({ news: 0, signals: 0 });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        sentimentApi.getSentimentSources().then(data => {
            setBreakdown(data);
            setLoading(false);
        }).catch(console.error);
    }, []);

    return (
        <div style={s.card}>
            <div style={s.cardHeader}>
                <span style={s.cardTitle}>Sentiment Sources</span>
                <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
                    <span style={{
                        width: 7, height: 7, borderRadius: "50%",
                        background: t.accentTeal,
                        display: "inline-block",
                    }} />
                    <span style={{ fontSize: 10.5, color: t.accentTeal, fontWeight: 600 }}>Engine Architecture</span>
                </span>
            </div>

            <div style={{ padding: "20px 16px" }}>
                <p style={{ fontSize: 13, color: t.textSecondary, marginBottom: 24, lineHeight: 1.5 }}>
                    This breakdown reflects the core data pipeline feeding the AI sentiment engine, split across natural language processing and quantitative market metrics.
                </p>

                {loading ? (
                    <div style={{ padding: "10px 0", color: t.textMuted, fontSize: 13, textAlign: "center" }}>
                        Loading sources...
                    </div>
                ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
                        {/* News NLP Bar */}
                        <div>
                            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                                <span style={{ fontSize: 12.5, fontWeight: 600, color: t.textPrimary }}>News NLP</span>
                                <span style={{ fontSize: 13, fontWeight: 700, color: t.accentTeal }}>{breakdown.news.toFixed(1)}%</span>
                            </div>
                            <div style={{ height: 8, borderRadius: 6, background: t.bgCard2, overflow: "hidden" }}>
                                <div style={{
                                    height: "100%", width: `${breakdown.news}%`,
                                    background: t.accentTeal, borderRadius: 6,
                                    transition: "width 1s ease-out"
                                }} />
                            </div>
                        </div>

                        {/* Market Signals Bar */}
                        <div>
                            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                                <span style={{ fontSize: 12.5, fontWeight: 600, color: t.textPrimary }}>Market Signals</span>
                                <span style={{ fontSize: 13, fontWeight: 700, color: t.accentBlue }}>{breakdown.signals.toFixed(1)}%</span>
                            </div>
                            <div style={{ height: 8, borderRadius: 6, background: t.bgCard2, overflow: "hidden" }}>
                                <div style={{
                                    height: "100%", width: `${breakdown.signals}%`,
                                    background: t.accentBlue, borderRadius: 6,
                                    transition: "width 1s ease-out"
                                }} />
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}