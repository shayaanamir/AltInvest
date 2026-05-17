import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";

function CubeIcon({ t }) {
    return (
        <svg width="72" height="72" viewBox="0 0 72 72" fill="none">
            {/* Isometric cube */}
            <polygon points="36,10 62,25 62,47 36,62 10,47 10,25" fill={t.bgCard2} stroke={t.borderLight} strokeWidth="1.2" />
            <polygon points="36,10 62,25 36,40 10,25" fill={t.accentBlue} fillOpacity="0.35" />
            <polygon points="10,25 36,40 36,62 10,47" fill={t.accentTeal} fillOpacity="0.45" />
            <polygon points="62,25 36,40 36,62 62,47" fill={t.accentBlue} fillOpacity="0.6" />
            {/* Sparkle */}
            <text x="34" y="32" fontSize="12" fill={t.textPrimary} opacity="0.8">✦</text>
        </svg>
    );
}

export default function AssetIntelligence() {
    const { tokens: t } = useTheme();
    const s = makeStyles(t);

    return (
        <div style={s.card}>
            <div style={{ padding: "12px 14px 10px", borderBottom: `1px solid ${t.border}` }}>
                <span style={s.cardTitle}>Alternative Asset Intelligence</span>
            </div>

            {/* Cube visual */}
            <div style={{
                display: "flex", flexDirection: "column", alignItems: "center",
                padding: "24px 14px 16px", gap: 6,
            }}>
                <CubeIcon t={t} />
                <span style={{ fontSize: 10.5, color: t.textMuted, fontWeight: 500 }}>AAI Score</span>
            </div>

            {/* Bottom metrics */}
            <div style={{
                display: "grid", gridTemplateColumns: "1fr 1fr",
                borderTop: `1px solid ${t.border}`,
            }}>
                <div style={{ padding: "12px 14px", borderRight: `1px solid ${t.border}` }}>
                    <div style={{ fontSize: 9.5, color: t.textMuted, fontWeight: 600, marginBottom: 6 }}>AI Recommendation</div>
                    <div style={{ fontSize: 14, fontWeight: 800, color: t.accentGreen, letterSpacing: "0.01em", lineHeight: 1.2 }}>
                        STRONG<br />BUY
                    </div>
                </div>
                <div style={{ padding: "12px 14px" }}>
                    <div style={{ fontSize: 9.5, color: t.textMuted, fontWeight: 600, marginBottom: 6 }}>Confidence</div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: t.accentGreen }}>92.4%</div>
                </div>
            </div>
        </div>
    );
}