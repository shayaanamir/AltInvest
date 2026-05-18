import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";

// Generate wave-like sentiment data
function wave(len, amp, freq, phase, base) {
    return Array.from({ length: len }, (_, i) => {
        const t = (i / len) * Math.PI * 2 * freq + phase;
        return base + amp * Math.sin(t) + (amp * 0.3) * Math.sin(t * 2.3 + 1) + (amp * 0.15) * Math.sin(t * 3.7 + 2);
    });
}

const N = 80;
const POS = wave(N, 28, 3.5, 0, 62);
const NEG = wave(N, 18, 3.2, 1.2, 32);

function buildPath(points, W, H, minY, rangeY) {
    return points
        .map((v, i) => {
            const x = (i / (points.length - 1)) * W;
            const y = H - ((v - minY) / rangeY) * H * 0.82 - H * 0.09;
            return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
        })
        .join(" ");
}

export default function GlobalSentimentChart() {
    const { tokens: t } = useTheme();
    const s = makeStyles(t);

    const W = 560, H = 200;
    const allPts = [...POS, ...NEG];
    const minY = Math.min(...allPts) - 5;
    const rangeY = Math.max(...allPts) - minY + 5;

    const posPath = buildPath(POS, W, H, minY, rangeY);
    const negPath = buildPath(NEG, W, H, minY, rangeY);

    return (
        <div style={s.card}>
            <div style={s.cardHeader}>
                <span style={{ ...s.cardTitle, display: "flex", alignItems: "center", gap: 7 }}>
                    <span style={{ fontSize: 14, color: t.accentBlue }}>〜</span>
                    Global Sentiment Trend (30D)
                </span>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <span style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11, color: t.accentGreen, fontWeight: 600 }}>
                        <span style={{ width: 8, height: 8, borderRadius: "50%", background: t.accentGreen, display: "inline-block" }} />
                        Positive
                    </span>
                    <span style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11, color: t.accentRed, fontWeight: 600 }}>
                        <span style={{ width: 8, height: 8, borderRadius: "50%", background: t.accentRed, display: "inline-block" }} />
                        Negative
                    </span>
                </div>
            </div>
            <div style={{ padding: "10px 14px 12px" }}>
                <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
                    <defs>
                        <linearGradient id="posGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor={t.accentGreen} stopOpacity="0.12" />
                            <stop offset="100%" stopColor={t.accentGreen} stopOpacity="0" />
                        </linearGradient>
                        <linearGradient id="negGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor={t.accentRed} stopOpacity="0.08" />
                            <stop offset="100%" stopColor={t.accentRed} stopOpacity="0" />
                        </linearGradient>
                    </defs>
                    <path d={`${posPath} L${W},${H} L0,${H} Z`} fill="url(#posGrad)" />
                    <path d={posPath} fill="none" stroke={t.accentGreen} strokeWidth="2" strokeLinejoin="round" />
                    <path d={`${negPath} L${W},${H} L0,${H} Z`} fill="url(#negGrad)" />
                    <path d={negPath} fill="none" stroke={t.accentRed} strokeWidth="2" strokeLinejoin="round" />
                </svg>
                {/* X labels */}
                <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6 }}>
                    {["Apr 1", "Apr 5", "Apr 10", "Apr 15", "Apr 20", "Apr 25", "Apr 30"].map(d => (
                        <span key={d} style={{ fontSize: 9, color: t.textMuted }}>{d}</span>
                    ))}
                </div>
            </div>
        </div>
    );
}