import { useState, useEffect } from "react";
import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";
import { assetApi } from "../../services/assetApi";

function getVolatilityMetrics(val, t) {
    if (val >= 60) return { tag: `High (${val})`, color: t.accentRed };
    if (val >= 30) return { tag: `Medium (${val})`, color: t.accentYellow };
    return { tag: `Low (${val})`, color: t.accentGreen };
}

function getLiquidityMetrics(val, t) {
    if (val >= 80) return { tag: `Excellent (${val})`, color: t.accentGreen };
    if (val >= 40) return { tag: `Good (${val})`, color: t.accentYellow };
    return { tag: `Poor (${val})`, color: t.accentRed };
}

function getGenericRiskMetrics(val, t) {
    if (val >= 60) return { tag: `High (${val})`, color: t.accentRed };
    if (val >= 30) return { tag: `Medium (${val})`, color: t.accentYellow };
    return { tag: `Low (${val})`, color: t.accentGreen };
}

export default function RiskAnalytics({ assetId = 101 }) {
    const { tokens: t } = useTheme();
    const s = makeStyles(t);

    const [risks, setRisks] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        assetApi.getAssetRiskMetrics(assetId).then(data => {
            if (data) {
                const vol = getVolatilityMetrics(data.volatility_index, t);
                const liq = getLiquidityMetrics(data.liquidity_score, t);
                const reg = getGenericRiskMetrics(data.regulatory_risk, t);
                const mkt = getGenericRiskMetrics(data.market_risk, t);

                setRisks([
                    { label: "Volatility Index", value: data.volatility_index, tag: vol.tag, color: vol.color },
                    { label: "Liquidity Score", value: data.liquidity_score, tag: liq.tag, color: liq.color },
                    { label: "Regulatory Risk", value: data.regulatory_risk, tag: reg.tag, color: reg.color },
                    { label: "Market Risk", value: data.market_risk, tag: mkt.tag, color: mkt.color }
                ]);
            }
            setLoading(false);
        }).catch(console.error);
    }, [assetId, t]);

    return (
        <div style={s.card}>
            <div style={{ padding: "11px 14px 10px", borderBottom: `1px solid ${t.border}` }}>
                <span style={{ ...s.cardTitle, display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ fontSize: 13, color: t.accentYellow }}>⚠</span> Risk Overview
                </span>
            </div>
            
            {loading ? (
                <div style={{ padding: "24px 14px", color: t.textMuted, fontSize: 13, textAlign: "center" }}>
                    Loading analytics...
                </div>
            ) : (
                <div style={{ padding: "12px 14px", display: "flex", flexDirection: "column", gap: 12 }}>
                    {risks.map((r) => (
                        <div key={r.label}>
                            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
                                <span style={{ fontSize: 11, color: t.textSecondary }}>{r.label}</span>
                                <span style={{ fontSize: 10.5, fontWeight: 600, color: r.color }}>{r.tag}</span>
                            </div>
                            <div style={{
                                height: 5, borderRadius: 4,
                                background: t.bgCard2, overflow: "hidden",
                            }}>
                                <div style={{
                                    height: "100%", borderRadius: 4,
                                    width: `${r.value}%`,
                                    background: r.color,
                                    transition: "width 0.6s ease",
                                }} />
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}