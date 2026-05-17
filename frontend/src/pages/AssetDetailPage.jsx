import { useTheme } from "../context/ThemeContext";
import { makeStyles } from "../styles/makeStyles";
import PriceChart from "../components/assetDetail/PriceChart";
import AssetIntelligence from "../components/assetDetail/AssetIntelligence";
import RiskAnalytics from "../components/assetDetail/RiskAnalytics";
import AboutAsset from "../components/assetDetail/AboutAsset";
import MarketDepth from "../components/assetDetail/MarketDepth";

export default function AssetDetailPage({ onNavigate }) {
    const { tokens: t } = useTheme();
    const s = makeStyles(t);

    return (
        <div style={s.content}>
            {/* Back nav */}
            <div
                style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 14, cursor: "pointer", width: "fit-content" }}
                onClick={() => onNavigate && onNavigate("Dashboard")}
            >
                <span style={{ fontSize: 13, color: t.textMuted }}>←</span>
                <span style={{ fontSize: 12, color: t.textMuted, fontWeight: 500 }}>Back to Dashboard</span>
            </div>

            {/* Asset header */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 18 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                    <div style={{
                        width: 52, height: 52, borderRadius: 12,
                        background: t.bgCard2, border: `1px solid ${t.borderLight}`,
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: 13, fontWeight: 800, color: "#f7931a",
                    }}>
                        BTC
                    </div>
                    <div>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <span style={{ fontSize: 22, fontWeight: 700, color: t.textPrimary, letterSpacing: "-0.5px" }}>Bitcoin</span>
                            <span style={{
                                fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 5,
                                background: t.bgCard2, border: `1px solid ${t.borderLight}`, color: t.textSecondary,
                            }}>BTC</span>
                            <span style={{
                                fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 5,
                                background: t.tagNeuBg, color: t.accentBlue, border: `1px solid ${t.accentBlue}33`,
                            }}>Crypto</span>
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 3 }}>
                            <span style={{ fontSize: 28, fontWeight: 700, color: t.textPrimary, letterSpacing: "-0.5px" }}>$64,230</span>
                            <span style={{ fontSize: 13, fontWeight: 600, color: t.accentGreen }}>↗ 2.45%</span>
                        </div>
                    </div>
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                    <button style={{
                        background: "rgba(255,64,96,0.15)", border: `1px solid ${t.accentRed}`,
                        borderRadius: 8, padding: "8px 22px", fontSize: 13, fontWeight: 700,
                        color: t.accentRed, cursor: "pointer",
                    }}>Sell</button>
                    <button style={{
                        background: t.btnPrimaryBg, border: "none",
                        borderRadius: 8, padding: "8px 22px", fontSize: 13, fontWeight: 700,
                        color: "#fff", cursor: "pointer",
                    }}>Buy</button>
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
                    <AboutAsset />
                </div>
            </div>
        </div>
    );
}