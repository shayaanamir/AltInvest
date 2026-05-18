import { useState, useEffect } from "react";
import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";
import { sentimentApi } from "../../services/sentimentApi";

// ── Fallback static wave (used when API has no history yet) ──────────────────
function wave(len, amp, freq, phase, base) {
    return Array.from({ length: len }, (_, i) => {
        const t = (i / len) * Math.PI * 2 * freq + phase;
        return base + amp * Math.sin(t) + (amp * 0.3) * Math.sin(t * 2.3 + 1) + (amp * 0.15) * Math.sin(t * 3.7 + 2);
    });
}

function buildPath(points, W, H, minY, rangeY) {
    return points
        .map((v, i) => {
            const x = (i / (points.length - 1)) * W;
            const y = H - ((v - minY) / rangeY) * H * 0.82 - H * 0.09;
            return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
        })
        .join(" ");
}

/**
 * Converts sentiment_score (0–1) to a 0–100 positive-signal value
 * and its inverse (1 – score) * 100 as the negative signal.
 */
function historyToChartPoints(history) {
    return history.map(h => ({
        pos: h.score * 100,
        neg: (1 - h.score) * 100,
        date: h.date,
    }));
}

// Build X-axis date labels from the history array
function buildLabels(history) {
    if (!history.length) return ["Apr 1", "Apr 5", "Apr 10", "Apr 15", "Apr 20", "Apr 25", "Apr 30"];
    const step = Math.max(1, Math.floor(history.length / 6));
    return history
        .filter((_, i) => i % step === 0)
        .slice(0, 7)
        .map(h => {
            if (!h.date) return "";
            try {
                return new Date(h.date).toLocaleDateString("en-US", { month: "short", day: "numeric" });
            } catch { return ""; }
        });
}

export default function GlobalSentimentChart() {
    const { tokens: t } = useTheme();
    const s = makeStyles(t);

    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Fetch BTC history as the primary trend signal
        sentimentApi.getSentimentHistory("btc", 30)
            .then(data => {
                setHistory(data);
                setLoading(false);
            })
            .catch(() => {
                setLoading(false); // Fall back to wave chart
            });
    }, []);

    const W = 560, H = 200;

    // ── Build chart paths ──────────────────────────────────────────────────────
    let posPoints, negPoints, labels;

    if (history.length >= 2) {
        const pts = historyToChartPoints(history);
        posPoints = pts.map(p => p.pos);
        negPoints = pts.map(p => p.neg);
        labels = buildLabels(history);
    } else {
        // No real history yet — fall back to animated wave
        const N = 80;
        posPoints = wave(N, 28, 3.5, 0,   62);
        negPoints = wave(N, 18, 3.2, 1.2, 32);
        labels = ["Apr 1", "Apr 5", "Apr 10", "Apr 15", "Apr 20", "Apr 25", "Apr 30"];
    }

    const allPts  = [...posPoints, ...negPoints];
    const minY    = Math.min(...allPts) - 5;
    const rangeY  = Math.max(...allPts) - minY + 5;

    const posPath = buildPath(posPoints, W, H, minY, rangeY);
    const negPath = buildPath(negPoints, W, H, minY, rangeY);

    const isLive = history.length >= 2;

    return (
        <div style={s.card}>
            <div style={s.cardHeader}>
                <span style={{ ...s.cardTitle, display: "flex", alignItems: "center", gap: 7 }}>
                    <span style={{ fontSize: 14, color: t.accentBlue }}>〜</span>
                    Global Sentiment Trend (30D)
                    {isLive && (
                        <span style={{
                            fontSize: 9.5, fontWeight: 600,
                            color: t.accentGreen,
                            background: "rgba(0,212,139,0.12)",
                            border: `1px solid ${t.accentGreen}44`,
                            padding: "2px 7px", borderRadius: 20,
                            marginLeft: 4,
                        }}>
                            LIVE
                        </span>
                    )}
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
                {loading ? (
                    <div style={{ height: H, display: "flex", alignItems: "center", justifyContent: "center", color: t.textMuted, fontSize: 13 }}>
                        Loading sentiment trend...
                    </div>
                ) : (
                    <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
                        <defs>
                            <linearGradient id="posGrad" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%"   stopColor={t.accentGreen} stopOpacity="0.12" />
                                <stop offset="100%" stopColor={t.accentGreen} stopOpacity="0" />
                            </linearGradient>
                            <linearGradient id="negGrad" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%"   stopColor={t.accentRed} stopOpacity="0.08" />
                                <stop offset="100%" stopColor={t.accentRed} stopOpacity="0" />
                            </linearGradient>
                        </defs>
                        <path d={`${posPath} L${W},${H} L0,${H} Z`} fill="url(#posGrad)" />
                        <path d={posPath} fill="none" stroke={t.accentGreen} strokeWidth="2" strokeLinejoin="round" />
                        <path d={`${negPath} L${W},${H} L0,${H} Z`} fill="url(#negGrad)" />
                        <path d={negPath} fill="none" stroke={t.accentRed}   strokeWidth="2" strokeLinejoin="round" />
                    </svg>
                )}
                {/* X-axis labels */}
                <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6 }}>
                    {labels.map((d, i) => (
                        <span key={i} style={{ fontSize: 9, color: t.textMuted }}>{d}</span>
                    ))}
                </div>
            </div>
        </div>
    );
}