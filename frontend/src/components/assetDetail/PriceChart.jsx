import { useState, useEffect, useRef } from "react";
import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";
import { assetApi } from "../../services/assetApi";
import { TIME_FILTERS } from "../../data/constants";

export default function PriceChart({ assetId = 101 }) {
    const { tokens: t } = useTheme();
    const s = makeStyles(t);
    const [activeTab, setActiveTab] = useState("1M");
    // activeMode is mostly for the UI legend now, since both lines are shown if available
    const [activeMode, setActiveMode] = useState("Price");

    const [history, setHistory] = useState([]);
    const [forecast, setForecast] = useState([]);
    const [loading, setLoading] = useState(true);

    const containerRef = useRef(null);
    const [dims, setDims] = useState({ W: 580, H: 220 });

    useEffect(() => {
        const ob = new ResizeObserver((entries) => {
            if (entries[0]) {
                setDims({
                    W: Math.max(100, entries[0].contentRect.width),
                    H: Math.max(100, entries[0].contentRect.height)
                });
            }
        });
        if (containerRef.current) ob.observe(containerRef.current);
        return () => ob.disconnect();
    }, []);

    useEffect(() => {
        setLoading(true);
        Promise.all([
            assetApi.getAssetPricePerformance(assetId, "Price", activeTab),
            assetApi.getAssetPricePerformance(assetId, "AI Prediction", activeTab)
        ]).then(([histData, foreData]) => {
            setHistory(histData);
            setForecast(foreData);
            setLoading(false);
        }).catch(console.error);
    }, [assetId, activeTab]);

    const { W, H } = dims;

    let content = null;

    if (loading) {
        content = <div style={{ height: H, display: "flex", alignItems: "center", justifyContent: "center", color: t.textMuted }}>Loading chart...</div>;
    } else if (history.length < 2) {
        content = <div style={{ height: H, display: "flex", alignItems: "center", justifyContent: "center", color: t.textMuted }}>Not enough data</div>;
    } else {
        const histVals = history.map(d => d.value);
        let allVals = [...histVals];
        
        // Always show forecast if we have data for it
        let showForecast = forecast.length > 0;
        if (showForecast) {
            allVals = [...allVals, ...forecast.map(d => d.value)];
        }

        const minVal = Math.min(...allVals) * 0.98;
        const maxVal = Math.max(...allVals) * 1.02;
        const range = maxVal - minVal;

        const totalPoints = history.length + (showForecast ? forecast.length - 1 : 0);

        const toPoint = (v, i, total) => {
            const x = 45 + (i / Math.max(1, total - 1)) * (W - 60);
            const y = H - 25 - ((v - minVal) / range) * (H - 40);
            return { x, y };
        };

        const histPts = history.map((d, i) => toPoint(d.value, i, totalPoints));
        const lastHist = histPts[histPts.length - 1];
        
        const pricePath = histPts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
        const priceArea = `${pricePath} L${lastHist.x.toFixed(1)},${H - 25} L${histPts[0].x.toFixed(1)},${H - 25} Z`;

        let forecastPath = null;
        let forecastStartX = null, forecastStartY = null;
        if (showForecast) {
            const forecastPts = forecast.map((d, i) => toPoint(d.value, history.length - 1 + i, totalPoints));
            forecastPts[0] = lastHist;
            forecastPath = forecastPts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
            forecastStartX = lastHist.x;
            forecastStartY = lastHist.y;
        }

        const yLabels = [];
        for (let i = 0; i < 4; i++) yLabels.push(minVal + (range * i) / 3);

        const xLabels = [];
        const fullTimeline = [...history, ...(showForecast ? forecast.slice(1) : [])];
        if (fullTimeline.length > 0) xLabels.push(fullTimeline[0].date);
        if (fullTimeline.length > 2) xLabels.push(fullTimeline[Math.floor(fullTimeline.length / 2)].date);
        if (fullTimeline.length > 1) xLabels.push(fullTimeline[fullTimeline.length - 1].date);

        content = (
            <svg width="100%" height="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: "block" }}>
                <defs>
                    <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={t.accentBlue} stopOpacity="0.18" />
                        <stop offset="100%" stopColor={t.accentBlue} stopOpacity="0.0" />
                    </linearGradient>
                </defs>

                {yLabels.map((v, i) => {
                    const y = H - 25 - ((v - minVal) / range) * (H - 40);
                    let labelText = "";
                    if (v >= 1000000) labelText = (v / 1000000).toFixed(1) + "M";
                    else if (v >= 1000) labelText = (v / 1000).toFixed(1) + "k";
                    else if (v >= 10) labelText = v.toFixed(0);
                    else labelText = v.toFixed(2);

                    return (
                        <g key={i}>
                            <line x1={45} y1={y} x2={W - 15} y2={y} stroke={t.border} strokeWidth="0.7" strokeDasharray="4,4" />
                            <text x={38} y={y + 4} fontSize="9.5" fill={t.textMuted} textAnchor="end">{labelText}</text>
                        </g>
                    );
                })}

                {xLabels.map((lb, i) => {
                    const x = 45 + (i / (xLabels.length - 1)) * (W - 60);
                    return (
                        <text key={i} x={x} y={H - 5} fontSize="9.5" fill={t.textMuted} textAnchor="middle">{lb.substring(5, 10)}</text>
                    );
                })}

                <path d={priceArea} fill="url(#priceGrad)" />
                <path d={pricePath} fill="none" stroke={t.accentBlue} strokeWidth="1.8" strokeLinejoin="round" />

                {showForecast && (
                    <>
                        <path 
                            d={forecastPath} 
                            fill="none" 
                            stroke="#9b6dff" 
                            strokeWidth="1.8" 
                            strokeDasharray="6,6" 
                            style={{ strokeDasharray: "6,6" }}
                            strokeLinejoin="round" 
                        />
                        <circle cx={forecastStartX} cy={forecastStartY} r="3.5" fill="#9b6dff" />
                    </>
                )}
            </svg>
        );
    }

    return (
        <div style={s.card}>
            <div style={s.cardHeader}>
                <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                    <span style={s.cardTitle}>Price Performance</span>
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
                                {m === "AI Prediction" && (
                                    <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#9b6dff", display: "inline-block" }} />
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

            <div style={{ flex: 1, position: "relative", minHeight: 220, margin: "16px 14px 10px" }}>
                <div ref={containerRef} style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0 }}>
                    {content}
                </div>
            </div>
        </div>
    );
}