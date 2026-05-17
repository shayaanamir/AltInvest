import { useState } from "react";
import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";

const TIME_FILTERS = ["1D", "1W", "1M", "3M", "1Y"];

// Generate a realistic-looking BTC price path for 1M
const PRICE_POINTS = [
    64800, 65200, 64900, 65800, 66100, 65500, 64700, 63900, 63200, 62800,
    62100, 61500, 61800, 62400, 63100, 63800, 64200, 63700, 63000, 62500,
    62900, 63500, 64100, 64600, 65000, 64400, 63800, 63200, 62800, 63500,
    64230,
];

// AI forecast continuation (dashed)
const FORECAST_POINTS = [
    64230, 64800, 65500, 66200, 65800, 66500, 67100, 67800, 68200, 68900,
];

function buildSvgPath(points, W, H, minY, rangeY) {
    return points
        .map((v, i) => {
            const x = (i / (points.length - 1)) * W;
            const y = H - ((v - minY) / rangeY) * H;
            return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
        })
        .join(" ");
}

export default function PriceChart() {
    const { tokens: t } = useTheme();
    const s = makeStyles(t);
    const [activeTab, setActiveTab] = useState("1M");
    const [activeMode, setActiveMode] = useState("Price");

    const W = 580, H = 220;
    const allPoints = [...PRICE_POINTS, ...FORECAST_POINTS.slice(1)];
    const minY = Math.min(...allPoints) - 500;
    const rangeY = Math.max(...allPoints) - minY + 500;

    const priceOffsetX = ((PRICE_POINTS.length - 1) / (allPoints.length - 1)) * W;

    const pricePath = buildSvgPath(PRICE_POINTS, priceOffsetX, H, minY, rangeY);
    const priceArea = `${pricePath} L${priceOffsetX.toFixed(1)},${H} L0,${H} Z`;

    const forecastStartX = priceOffsetX;
    const forecastStartY = H - ((PRICE_POINTS[PRICE_POINTS.length - 1] - minY) / rangeY) * H;

    const forecastPath = FORECAST_POINTS.map((v, i) => {
        const x = forecastStartX + (i / (FORECAST_POINTS.length - 1)) * (W - forecastStartX);
        const y = H - ((v - minY) / rangeY) * H;
        return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");

    return (
        <div style={s.card}>
            <div style={s.cardHeader}>
                <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                    <span style={s.cardTitle}>Price &amp; AI Forecast</span>
                    <div style={{ display: "flex", gap: 12 }}>
                        {["Price", "AI Prediction"].map(m => (
                            <button key={m} onClick={() => setActiveMode(m)} style={{
                                background: "none", border: "none", cursor: "pointer", padding: 0,
                                fontSize: 11.5, fontWeight: 600,
                                color: activeMode === m ? t.textPrimary : t.textMuted,
                                display: "flex", alignItems: "center", gap: 5,
                            }}>
                                {m === "Price" && (
                                    <span style={{ width: 8, height: 8, borderRadius: "50%", background: t.accentBlue, display: "inline-block" }} />
                                )}
                                {m}
                            </button>
                        ))}
                    </div>
                </div>
                <div style={s.timeFilters}>
                    {TIME_FILTERS.map(f => (
                        <button key={f} onClick={() => setActiveTab(f)} style={{
                            ...s.timeBtn,
                            ...(activeTab === f ? s.timeBtnActive : {}),
                        }}>{f}</button>
                    ))}
                </div>
            </div>

            <div style={{ padding: "16px 14px 10px", position: "relative" }}>
                <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
                    <defs>
                        <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor={t.accentBlue} stopOpacity="0.18" />
                            <stop offset="100%" stopColor={t.accentBlue} stopOpacity="0.0" />
                        </linearGradient>
                    </defs>

                    {/* Price area fill */}
                    <path d={priceArea} fill="url(#priceGrad)" />

                    {/* Price line */}
                    <path d={pricePath} fill="none" stroke={t.accentBlue} strokeWidth="1.8" strokeLinejoin="round" />

                    {/* Forecast dashed line */}
                    <path
                        d={forecastPath}
                        fill="none"
                        stroke="#9b6dff"
                        strokeWidth="1.8"
                        strokeDasharray="5,4"
                        strokeLinejoin="round"
                    />

                    {/* Forecast start dot */}
                    <circle cx={forecastStartX} cy={forecastStartY} r="3.5" fill="#9b6dff" />
                </svg>

                {/* X-axis labels */}
                <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4 }}>
                    {["Apr 1", "Apr 8", "Apr 15", "Apr 22", "Apr 30", "May 7"].map(d => (
                        <span key={d} style={{ fontSize: 9.5, color: t.textMuted }}>{d}</span>
                    ))}
                </div>
            </div>
        </div>
    );
}