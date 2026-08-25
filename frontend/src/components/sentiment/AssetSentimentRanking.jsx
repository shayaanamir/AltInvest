import { useState, useEffect } from "react";
import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";
import { sentimentApi } from "../../services/sentimentApi";

/**
 * Fetches the real sentiment for all assets and ranks them by score.
 * Falls back gracefully to an empty list while loading or on error.
 */
export default function AssetSentimentRanking() {
    const { tokens: t } = useTheme();
    const s = makeStyles(t);

    const [assets, setAssets] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        sentimentApi.getSentimentData()
            .then(({ rawData }) => {
                // Build ranked list from the real engine output
                const ranked = [...rawData]
                    .sort((a, b) => b.sentiment_score - a.sentiment_score)
                    .map((asset, idx) => {
                        const dist = asset.sentiment_distribution ?? {};
                        // Engine uses { Positive, Negative, neutral } (note caps)
                        const pos = dist.Positive ?? dist.positive ?? 0;
                        const neg = dist.Negative ?? dist.negative ?? 0;
                        const neu = dist.neutral   ?? dist.Neutral  ?? 0;
                        const total = pos + neg + neu || 1;

                        const bullish  = Math.round((pos / total) * 100);
                        const bearish  = Math.round((neg / total) * 100);
                        const neutral  = 100 - bullish - bearish;
                        const score    = asset.sentiment_score ?? 0.5;

                        let label      = "Neutral";
                        let labelColor = "neutral";
                        if (score >= 0.55) { label = "Bullish"; labelColor = "green"; }
                        else if (score <= 0.45) { label = "Bearish"; labelColor = "red"; }

                        return {
                            rank:       idx + 1,
                            sym:        (asset.asset_id ?? asset.asset ?? "???").toUpperCase(),
                            bullish,
                            neutral,
                            bearish,
                            label,
                            labelColor,
                        };
                    });

                setAssets(ranked);
                setLoading(false);
            })
            .catch(err => {
                console.error("AssetSentimentRanking fetch error:", err);
                setLoading(false);
            });
    }, []);

    const labelColor = (c) =>
        c === "green" ? t.accentGreen : c === "red" ? t.accentRed : t.textMuted;

    return (
        <div style={s.card}>
            <div style={s.cardHeader}>
                <span style={s.cardTitle}>Asset Sentiment Ranking</span>
                {!loading && (
                    <span style={{ fontSize: 10, color: t.textMuted }}>
                        Live · {assets.length} assets
                    </span>
                )}
            </div>
            <div>
                {loading ? (
                    <div style={{ padding: "30px 16px", color: t.textMuted, fontSize: 13, textAlign: "center" }}>
                        Loading rankings...
                    </div>
                ) : assets.length === 0 ? (
                    <div style={{ padding: "30px 16px", color: t.textMuted, fontSize: 13, textAlign: "center" }}>
                        No data available.
                    </div>
                ) : (
                    assets.map((a, i) => (
                        <div key={a.sym} style={{
                            display: "grid", gridTemplateColumns: "22px 56px 1fr 70px",
                            alignItems: "center", gap: 10,
                            padding: "11px 16px",
                            borderBottom: i < assets.length - 1 ? `1px solid ${t.border}` : "none",
                        }}>
                            {/* Rank */}
                            <span style={{ fontSize: 11, color: t.textMuted, fontWeight: 600 }}>{a.rank}</span>

                            {/* Symbol */}
                            <span style={{ fontSize: 12.5, fontWeight: 700, color: t.textPrimary }}>{a.sym}</span>

                            {/* Sentiment bar */}
                            <div style={{ height: 7, borderRadius: 4, overflow: "hidden", background: t.bgCard2, display: "flex" }}>
                                <div style={{ width: `${a.bullish}%`, background: t.accentGreen, transition: "width 0.8s ease" }} />
                                <div style={{ width: `${a.neutral}%`, background: t.borderLight }} />
                                <div style={{ width: `${a.bearish}%`, background: t.accentRed }} />
                            </div>

                            {/* Label */}
                            <span style={{ fontSize: 11, fontWeight: 700, color: labelColor(a.labelColor), textAlign: "right" }}>
                                {a.label}
                            </span>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}