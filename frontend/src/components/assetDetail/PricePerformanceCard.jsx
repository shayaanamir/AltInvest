import { useState, useMemo } from "react";
import { useElementSize } from "../../hooks/useElementSize";
import { deriveAaiSignal } from "../../services/assetDetailApi";

const FILTERS = ["1D", "1W", "1M", "3M", "1Y"];
const DAY_MS = 86400000;

function daysApart(a, b) {
  return Math.round((new Date(a).getTime() - new Date(b).getTime()) / DAY_MS);
}

function sliceForFilter(arr, filter) {
  if (!arr) return arr;
  if (filter === "1D") return arr.slice(-2);
  if (filter === "1W") return arr.slice(-4);
  return arr; // 1M / 3M / 1Y — sample data only has one history window
}

function formatY(v) {
  if (v >= 1000) return `$${(v / 1000).toFixed(1)}K`;
  if (v >= 1) return `$${v.toFixed(2)}`;
  return `$${v.toFixed(4)}`;
}

export default function PricePerformanceCard({ priceHistory, forecast, aaiPanel }) {
  const [mode, setMode] = useState("Price");
  const [filter, setFilter] = useState("1M");
  const [containerRef, dims] = useElementSize({ W: 900, H: 320 });

  const history = useMemo(() => sliceForFilter(priceHistory, filter), [priceHistory, filter]);
  const safeForecast = forecast || [];
  const showForecast = mode === "AI Prediction" && safeForecast.length > 0 && history?.length > 1;

  const chart = useMemo(() => {
    if (!history || history.length < 2) return null;

    const { W, H } = dims;
    const PAD_L = 58, PAD_R = 16, PAD_T = 18, PAD_B = 28;
    const plotW = W - PAD_L - PAD_R;
    const plotH = H - PAD_T - PAD_B;

    const historyShare = showForecast ? 0.66 : 1;
    const lastDate = history[history.length - 1].date;
    const firstDate = history[0].date;
    const totalSpan = Math.max(1, daysApart(lastDate, firstDate));
    const forecastSpan = showForecast
      ? Math.max(1, daysApart(safeForecast[safeForecast.length - 1].date, lastDate))
      : 1;

    const values = [
      ...history.map((d) => d.price),
      ...(showForecast ? safeForecast.map((d) => d.price) : []),
    ];
    const minV = Math.min(...values) * 0.985;
    const maxV = Math.max(...values) * 1.015;
    const vRange = Math.max(1e-9, maxV - minV);

    const yFor = (v) => PAD_T + plotH - ((v - minV) / vRange) * plotH;
    const xForHistory = (date) => {
      const agoDays = daysApart(lastDate, date);
      const t = totalSpan === 0 ? 1 : 1 - agoDays / totalSpan;
      return PAD_L + plotW * historyShare * t;
    };
    const xForForecast = (date) => {
      const aheadDays = daysApart(date, lastDate);
      const t = Math.min(1, aheadDays / forecastSpan);
      return PAD_L + plotW * historyShare + plotW * (1 - historyShare) * t;
    };

    const histPts = history.map((d) => ({ x: xForHistory(d.date), y: yFor(d.price), date: d.date }));
    const last = histPts[histPts.length - 1];
    const linePath = histPts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
    const areaPath = `${linePath} L ${last.x.toFixed(1)} ${PAD_T + plotH} L ${histPts[0].x.toFixed(1)} ${PAD_T + plotH} Z`;

    let forecastPath = "";
    let forecastPts = [];
    if (showForecast) {
      forecastPts = safeForecast.map((d) => ({ x: xForForecast(d.date), y: yFor(d.price), date: d.date }));
      const pts = [{ x: last.x, y: last.y }, ...forecastPts];
      forecastPath = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
    }

    const yTicks = [0, 1, 2, 3].map((i) => minV + (vRange * i) / 3);
    const xLabels = histPts.map((p) => {
      const ago = daysApart(lastDate, p.date);
      return { x: p.x, label: ago === 0 ? "Today" : `${ago}d` };
    });
    const forecastLabels = forecastPts.map((p) => ({
      x: p.x,
      label: `+${daysApart(p.date, lastDate)}d`,
    }));

    return { W, H, PAD_L, PAD_R, PAD_T, plotH, linePath, areaPath, forecastPath, last, yTicks, yFor, xLabels, forecastLabels };
  }, [history, dims, showForecast, safeForecast]);

  const signal = aaiPanel ? deriveAaiSignal(aaiPanel.score) : null;

  return (
    <div className="sv2-card adt-chart-card">
      <div className="adt-chart-head">
        <div>
          <div className="sv2-card-title">Price performance</div>
          {showForecast && (
            <div className="adt-chart-sub">Dashed line is the model's forward path, branching from today</div>
          )}
        </div>
        <div className="adt-chart-controls">
          <div className="sv2-segmented">
            {["Price", "AI Prediction"].map((m) => (
              <button key={m} className={mode === m ? "active" : ""} onClick={() => setMode(m)}>{m}</button>
            ))}
          </div>
          <div className="sv2-segmented">
            {FILTERS.map((f) => (
              <button key={f} className={filter === f ? "active" : ""} onClick={() => setFilter(f)}>{f}</button>
            ))}
          </div>
        </div>
      </div>

      <div className="adt-chart-body" ref={containerRef}>
        {!chart ? (
          <div className="adt-chart-empty">Not enough price data yet.</div>
        ) : (
          <svg width="100%" height="100%" viewBox={`0 0 ${chart.W} ${chart.H}`} preserveAspectRatio="none">
            <defs>
              <linearGradient id="adtPriceGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--sv2-accent)" stopOpacity="0.22" />
                <stop offset="100%" stopColor="var(--sv2-accent)" stopOpacity="0" />
              </linearGradient>
            </defs>

            {chart.yTicks.map((v, i) => {
              const y = chart.yFor(v);
              return (
                <g key={i}>
                  <line x1={chart.PAD_L} y1={y} x2={chart.W - chart.PAD_R} y2={y} stroke="var(--sv2-border)" strokeWidth="0.7" strokeDasharray="4,4" />
                  <text x={chart.PAD_L - 10} y={y + 4} fontSize="10.5" fill="var(--sv2-text-mute)" textAnchor="end">{formatY(v)}</text>
                </g>
              );
            })}

            {chart.xLabels.map((l, i) => (
              <text key={i} x={l.x} y={chart.H - 8} fontSize="10" fill="var(--sv2-text-mute)" textAnchor="middle">{l.label}</text>
            ))}
            {chart.forecastLabels.map((l, i) => (
              <text key={`f${i}`} x={l.x} y={chart.H - 8} fontSize="10" fill="var(--sv2-text-mute)" textAnchor="middle">{l.label}</text>
            ))}

            <path d={chart.areaPath} fill="url(#adtPriceGrad)" />
            <path d={chart.linePath} fill="none" stroke="var(--sv2-accent)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />

            {showForecast && (
              <>
                <line x1={chart.last.x} y1={chart.PAD_T} x2={chart.last.x} y2={chart.PAD_T + chart.plotH} stroke="var(--sv2-border-strong)" strokeWidth="1" strokeDasharray="3,3" />
                <text x={chart.last.x} y={chart.PAD_T - 5} fontSize="9.5" fill="var(--sv2-text-mute)" textAnchor="middle">today</text>
                <path d={chart.forecastPath} fill="none" stroke="var(--sv2-text-soft)" strokeWidth="2" strokeDasharray="6,5" strokeLinecap="round" />
                <circle cx={chart.last.x} cy={chart.last.y} r="3.5" fill="var(--sv2-text-soft)" />
              </>
            )}
          </svg>
        )}
      </div>

      <div className="adt-chart-foot">
        {showForecast ? (
          <div className="adt-legend">
            <span><span className="adt-legend-swatch solid" /> Actual</span>
            <span><span className="adt-legend-swatch dashed" /> Predicted</span>
          </div>
        ) : <span />}
        {showForecast && signal && (
          <div className="adt-signal-badge">
            Signal
            <span className={`adt-signal-pill ${signal.tone}`}>{signal.label.replace("Strong ", "")}</span>
            {aaiPanel?.confidence != null && (
              <span className="adt-signal-conf">{Math.round(aaiPanel.confidence * 100)}% confidence</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}