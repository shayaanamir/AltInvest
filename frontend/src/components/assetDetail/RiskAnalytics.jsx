import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";

const RISKS = [
    { label: "Volatility Index", value: 68, tag: "High (68)", tagColor: "#ff4060", barColor: "#ff4060" },
    { label: "Liquidity Score", value: 94, tag: "Excellent (94)", tagColor: "#00d48b", barColor: "#00d48b" },
    { label: "Regulatory Risk", value: 45, tag: "Medium (45)", tagColor: "#f5b731", barColor: "#f5b731" },
];

export default function RiskAnalytics() {
    const { tokens: t } = useTheme();
    const s = makeStyles(t);

    return (
        <div style={s.card}>
            <div style={{ padding: "11px 14px 10px", borderBottom: `1px solid ${t.border}` }}>
                <span style={{ ...s.cardTitle, display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ fontSize: 13, color: t.accentYellow }}>⚠</span> Risk Analytics
                </span>
            </div>
            <div style={{ padding: "12px 14px", display: "flex", flexDirection: "column", gap: 12 }}>
                {RISKS.map((r) => (
                    <div key={r.label}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
                            <span style={{ fontSize: 11, color: t.textSecondary }}>{r.label}</span>
                            <span style={{ fontSize: 10.5, fontWeight: 600, color: r.tagColor }}>{r.tag}</span>
                        </div>
                        <div style={{
                            height: 5, borderRadius: 4,
                            background: t.bgCard2, overflow: "hidden",
                        }}>
                            <div style={{
                                height: "100%", borderRadius: 4,
                                width: `${r.value}%`,
                                background: r.barColor,
                                transition: "width 0.6s ease",
                            }} />
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}