import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";

export default function PortfolioStats() {
    const { tokens: t } = useTheme();
    const s = makeStyles(t);

    return (
        <div style={s.portfolioStatsRow}>
            {/* Total Balance */}
            <div style={s.statCard}>
                <div style={s.statLabel}>Total Balance</div>
                <div style={{
                    ...s.statBadge,
                    background: t.tagGreenBg,
                    color: t.accentGreen,
                    marginBottom: 8,
                }}>
                    ↗ 2.85%
                </div>
                <div style={s.statValue}>$124,600</div>
            </div>

            {/* Total Profit / Loss */}
            <div style={s.statCard}>
                <div style={s.statLabel}>Total Profit/Loss</div>
                <div style={{
                    ...s.statBadge,
                    background: t.tagGreenBg,
                    color: t.accentGreen,
                    marginBottom: 8,
                }}>
                    ↗ 12.4%
                </div>
                <div style={s.statValue}>$14,250</div>
            </div>

            {/* Diversification Score */}
            <div style={{ ...s.statCard, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div>
                    <div style={s.statLabel}>Diversification Score</div>
                    <div style={{ display: "flex", alignItems: "baseline", gap: 3, margin: "10px 0 6px" }}>
                        <span style={{ ...s.statValue, fontSize: 32 }}>72</span>
                        <span style={{ fontSize: 13, color: t.textMuted, fontWeight: 500 }}>/100</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                        <span style={{ fontSize: 11, color: t.accentYellow }}>⚠</span>
                        <span style={{ fontSize: 10.5, color: t.accentYellow }}>Needs rebalancing</span>
                    </div>
                </div>
                {/* Score ring */}
                <div style={s.diversificationRing}>
                    <svg width="64" height="64" viewBox="0 0 64 64">
                        <circle cx="32" cy="32" r="26" fill="none" stroke={t.border} strokeWidth="5" />
                        <circle
                            cx="32" cy="32" r="26"
                            fill="none"
                            stroke={t.accentYellow}
                            strokeWidth="5"
                            strokeDasharray={`${(72 / 100) * 163.4} 163.4`}
                            strokeLinecap="round"
                            transform="rotate(-90 32 32)"
                        />
                    </svg>
                    <div style={s.diversificationRingLabel}>Fair</div>
                </div>
            </div>
        </div>
    );
}