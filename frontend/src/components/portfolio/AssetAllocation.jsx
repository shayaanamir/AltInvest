import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";

const ALLOCATIONS = [
    { label: "Crypto", pct: 65, color: "#4b8dff" },
    { label: "NFTs", pct: 15, color: "#00c9b0" },
    { label: "RWA", pct: 12, color: "#f5b731" },
    { label: "Commodities", pct: 8, color: "#00d48b" },
];

function DonutChart({ data, t }) {
    const cx = 80, cy = 80, r = 60, stroke = 22;
    const circumference = 2 * Math.PI * r;
    let offset = 0;

    return (
        <svg width="160" height="160" viewBox="0 0 160 160">
            {data.map((seg, i) => {
                const dash = (seg.pct / 100) * circumference;
                const gap = circumference - dash;
                const seg_offset = offset;
                offset += dash;
                return (
                    <circle
                        key={i}
                        cx={cx} cy={cy} r={r}
                        fill="none"
                        stroke={seg.color}
                        strokeWidth={stroke}
                        strokeDasharray={`${dash} ${gap}`}
                        strokeDashoffset={-seg_offset + circumference * 0.25}
                        style={{ transform: "rotate(-90deg)", transformOrigin: "80px 80px" }}
                    />
                );
            })}
            {/* center label */}
            <text x="80" y="76" textAnchor="middle" fill={t.textPrimary} fontSize="18" fontWeight="700">100%</text>
        </svg>
    );
}

export default function AssetAllocation() {
    const { tokens: t } = useTheme();
    const s = makeStyles(t);

    return (
        <div style={s.card}>
            <div style={s.cardHeader}>
                <span style={{ ...s.cardTitle, display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ fontSize: 14, color: t.accentBlue }}>◎</span> Asset Allocation
                </span>
            </div>
            <div style={{ padding: "16px 14px", display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
                <DonutChart data={ALLOCATIONS} t={t} />
                <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: 7 }}>
                    {ALLOCATIONS.map((a) => (
                        <div key={a.label} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                                <div style={{ width: 8, height: 8, borderRadius: "50%", background: a.color, flexShrink: 0 }} />
                                <span style={{ fontSize: 11.5, color: t.textSecondary }}>{a.label}</span>
                            </div>
                            <span style={{ fontSize: 11.5, fontWeight: 600, color: t.textPrimary }}>{a.pct}%</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}