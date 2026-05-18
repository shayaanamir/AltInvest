import { useState, useEffect } from "react";
import { useTheme } from "../context/ThemeContext";
import { makeStyles } from "../styles/makeStyles";
import PriceChart from "../components/assetDetail/PriceChart";
import MarketDepth from "../components/assetDetail/MarketDepth";
import AssetIntelligence from "../components/assetDetail/AssetIntelligence";
import RiskAnalytics from "../components/assetDetail/RiskAnalytics";
import AboutAsset from "../components/assetDetail/AboutAsset";
import { assetApi } from "../services/assetApi";

export default function AssetDetailPage({ onNavigate }) {
    const { tokens: t } = useTheme();
    const s = makeStyles(t);

    const [headerData, setHeaderData] = useState(null);

    useEffect(() => {
        assetApi.getAssetHeader(101).then(setHeaderData).catch(console.error);
    }, []);

    return (
        <div style={s.content} >
            {/* Back nav */}
            <div
                style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 14, cursor: "pointer", width: "fit-content" }}
                onClick={() => onNavigate && onNavigate("Dashboard")}
            >
                <span style={{ fontSize: 13, color: t.textMuted }}>←</span>
                <span style={{ fontSize: 12, color: t.textMuted, fontWeight: 500 }}>Back to Dashboard</span>
            </div>

            {/* Asset header */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 18, opacity: headerData ? 1 : 0.5 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                    <div style={{
                        width: 52, height: 52, borderRadius: 12,
                        background: t.bgCard2, border: `1px solid ${t.borderLight}`,
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: 13, fontWeight: 800, color: "#f7931a",
                    }}>
                        {headerData?.symbol || "..."}
                    </div>
                    <div>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <span style={{ fontSize: 22, fontWeight: 700, color: t.textPrimary, letterSpacing: "-0.5px" }}>{headerData?.name || "Loading..."}</span>
                            <span style={{
                                fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 5,
                                background: t.bgCard2, border: `1px solid ${t.borderLight}`, color: t.textSecondary,
                            }}>{headerData?.symbol || "..."}</span>
                            <span style={{
                                fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 5,
                                background: t.tagNeuBg, color: t.accentBlue, border: `1px solid ${t.accentBlue}33`,
                                textTransform: "capitalize"
                            }}>{headerData?.asset_type || "..."}</span>
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 3 }}>
                            <span style={{ fontSize: 28, fontWeight: 700, color: t.textPrimary, letterSpacing: "-0.5px" }}>
                                {headerData ? "$" + headerData.price.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 }) : "$0.00"}
                            </span>
                            <span style={{ fontSize: 13, fontWeight: 600, color: headerData?.change >= 0 ? t.accentGreen : t.accentRed }}>
                                {headerData?.change >= 0 ? "↗" : "↘"} {headerData ? Math.abs(headerData.change) : "0"}%
                            </span>
                        </div>
                    </div>
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                    <button style={{
                        background: "transparent", border: `1px solid ${t.border}`,
                        borderRadius: 8, padding: "8px 22px", fontSize: 13, fontWeight: 700,
                        color: t.textPrimary, cursor: "pointer",
                    }}>Add to Watchlist</button>
                    <button style={{
                        background: t.accentBlue, border: "none",
                        borderRadius: 8, padding: "8px 22px", fontSize: 13, fontWeight: 700,
                        color: "#fff", cursor: "pointer",
                    }}>Track Sentiment</button>
                </div>
            </div>

            {/* Main grid */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: 10 }}>
                {/* Left column */}
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    <PriceChart />
                    <MarketDepth />
                </div>

                {/* Right column */}
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    <AssetIntelligence />
                    <RiskAnalytics />
                    {/* <AboutAsset /> */}
                </div>
            </div>
        </div>
    );
}