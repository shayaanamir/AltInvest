import { useState, useEffect } from "react";
import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";
import { assetApi } from "../../services/assetApi";

function formatCurrencyCompact(val) {
    if (!val) return "$0";
    if (val >= 1000000000000) return "$" + (val / 1000000000000).toFixed(2) + "T";
    if (val >= 1000000000) return "$" + (val / 1000000000).toFixed(2) + "B";
    if (val >= 1000000) return "$" + (val / 1000000).toFixed(2) + "M";
    return "$" + val.toLocaleString();
}

function formatSupplyCompact(val) {
    if (!val) return "0";
    if (val >= 1000000000) return (val / 1000000000).toFixed(1) + "B";
    if (val >= 1000000) return (val / 1000000).toFixed(1) + "M";
    if (val >= 1000) return (val / 1000).toFixed(1) + "k";
    return val.toLocaleString();
}

export default function MarketDepth({ assetId = 101 }) {
    const { tokens: t } = useTheme();
    const s = makeStyles(t);

    const [stats, setStats] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        assetApi.getAssetMarketStats(assetId).then(data => {
            if (data) {
                setStats([
                    { label: "Market Rank", value: `#${data.market_rank} by Cap` },
                    { label: "Market Cap", value: formatCurrencyCompact(data.market_cap) },
                    { label: "24h Volume", value: formatCurrencyCompact(data.volume_24h) },
                    { label: "Circulating Supply", value: formatSupplyCompact(data.circulating_supply) },
                    { label: "All Time High", value: "$" + data.ath.toLocaleString() },
                ]);
            }
            setLoading(false);
        }).catch(console.error);
    }, [assetId]);

    return (
        <div style={s.card}>
            <div style={{ padding: "11px 14px 10px", borderBottom: `1px solid ${t.border}` }}>
                <span style={{ ...s.cardTitle, display: "flex", alignItems: "center", gap: 6 }}>
                    Market Statistics
                </span>
            </div>
            {loading ? (
                <div style={{ padding: "24px 14px", color: t.textMuted, fontSize: 13, textAlign: "center" }}>
                    Loading stats...
                </div>
            ) : (
                <div style={{
                    display: "grid", gridTemplateColumns: "repeat(5, 1fr)",
                }}>
                    {stats.map((stat, i) => (
                        <div key={stat.label} style={{
                            padding: "12px 16px",
                            borderRight: i < stats.length - 1 ? `1px solid ${t.border}` : "none",
                        }}>
                            <div style={{ fontSize: 10, color: t.textMuted, fontWeight: 500, marginBottom: 5 }}>{stat.label}</div>
                            <div style={{ fontSize: 13.5, fontWeight: 700, color: t.textPrimary, whiteSpace: "nowrap" }}>{stat.value}</div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}