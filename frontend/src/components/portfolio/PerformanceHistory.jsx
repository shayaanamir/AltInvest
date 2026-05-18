import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";

// Minimal sparkline data for the chart
const PERF_DATA = [
    { x: 0, y: 60 }, { x: 1, y: 55 }, { x: 2, y: 65 }, { x: 3, y: 58 },
    { x: 4, y: 72 }, { x: 5, y: 68 }, { x: 6, y: 80 }, { x: 7, y: 75 },
    { x: 8, y: 85 }, { x: 9, y: 78 }, { x: 10, y: 90 }, { x: 11, y: 88 },
];

function buildPath(data, width, height) {
    const minY = Math.min(...data.map(d => d.y));
    const maxY = Math.max(...data.map(d => d.y));
    const rangeY = maxY - minY || 1;
    const points = data.map(d => ({
        px: (d.x / (data.length - 1)) * width,
        py: height - ((d.y - minY) / rangeY) * height,
    }));
    const line = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.px.toFixed(1)},${p.py.toFixed(1)}`).join(" ");
    const area = `${line} L${(data.length - 1) / (data.length - 1) * width},${height} L0,${height} Z`;
    return { line, area };
}

export default function PerformanceHistory() {
    const { tokens: t } = useTheme();
    const s = makeStyles(t);
    const W = 520, H = 160;
    const { line, area } = buildPath(PERF_DATA, W, H);

    return (
        <div style={s.card}>
            <div style={s.cardHeader}>
                <span style={s.cardTitle}>Performance History</span>
            </div>
            <div style={{ padding: "14px 14px 10px", height: 200, position: "relative" }}>
                <svg width="100%" height="100%" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
                    <defs>
                        <linearGradient id="perfGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor={t.accentBlue} stopOpacity="0.25" />
                            <stop offset="100%" stopColor={t.accentBlue} stopOpacity="0.0" />
                        </linearGradient>
                    </defs>
                    <path d={area} fill="url(#perfGrad)" />
                    <path d={line} fill="none" stroke={t.accentBlue} strokeWidth="2" strokeLinejoin="round" />
                </svg>
                {/* X-axis labels */}
                <div style={{
                    display: "flex", justifyContent: "space-between",
                    padding: "4px 0 0", position: "absolute", bottom: 6, left: 14, right: 14,
                }}>
                    {["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].map(m => (
                        <span key={m} style={{ fontSize: 9, color: t.textMuted }}>{m}</span>
                    ))}
                </div>
            </div>
        </div>
    );
}