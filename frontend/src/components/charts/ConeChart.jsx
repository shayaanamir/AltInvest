import { useState, useMemo } from "react";
import { useElementSize } from "../../hooks/useElementSize";
import { CONE_DAYS, futureShare, shortDate } from "../../utils/volCone";

const DAY_MS = 86400000;

function daysApart(a, b) {
  return Math.round((new Date(a).getTime() - new Date(b).getTime()) / DAY_MS);
}

const fmtPath = (pts) => pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(" ");

/**
 * History line that continues into the illustrative 30-day volatility cone (ml/docs/DECISIONS.md D52), shared by
 * the asset price chart and the NFT floor chart. There is never a forecast or center line.
 *
 * history: [{date, price}] oldest first; layers / cone: from utils/volCone.chartLayers or utils/nftCone.nftChartLayers;
 * formatAxis / formatValue: number -> label; startText: the cone start label ("Last close, 8 Nov").
 */
export default function ConeChart({ history, layers, cone, formatAxis, formatValue, startText, emptyText, gradientId }) {
  const [containerRef, dims] = useElementSize({ W: 900, H: 320 });

  const chart = useMemo(() => {
    if (!layers.includes("history")) return null;

    // A minimum drawing width keeps the plot area positive in very narrow containers; the SVG then scales down.
    const W = Math.max(dims.W, 300);
    const H = dims.H;
    const narrow = W < 520;
    const PAD_L = 58, PAD_R = 16, PAD_T = 18, PAD_B = 28;
    const plotW = W - PAD_L - PAD_R;
    const plotH = H - PAD_T - PAD_B;

    // Time axis: history days, then CONE_DAYS more when the cone is drawn. Each section is linear; the future one
    // gets its true time share but at least MIN_FUTURE_SHARE of the width (D52), so it stays readable at 1Y.
    const firstDate = history[0].date;
    const lastDate = history[history.length - 1].date;
    const histSpan = Math.max(1, daysApart(lastDate, firstDate));
    const futW = cone ? plotW * futureShare(histSpan) : 0;
    const histW = plotW - futW;
    const xForDay = (day) => (day <= histSpan
      ? PAD_L + (histW * day) / histSpan
      : PAD_L + histW + (futW * (day - histSpan)) / CONE_DAYS);

    const values = [...history.map((d) => d.price), ...(cone ? cone.flatMap((c) => [c.outer.lower, c.outer.upper]) : [])];
    const minV = Math.min(...values) * 0.985;
    const maxV = Math.max(...values) * 1.015;
    const vRange = Math.max(1e-9, maxV - minV);
    const yFor = (v) => PAD_T + plotH - ((v - minV) / vRange) * plotH;

    const histPts = history.map((d) => ({ x: xForDay(daysApart(d.date, firstDate)), y: yFor(d.price), date: d.date, price: d.price }));
    const last = histPts[histPts.length - 1];
    const linePath = fmtPath(histPts.map((p) => [p.x, p.y]));
    const areaPath = `${linePath} L ${last.x.toFixed(1)} ${PAD_T + plotH} L ${histPts[0].x.toFixed(1)} ${PAD_T + plotH} Z`;

    // Each band: its upper edge forward in time, then its lower edge back to the start (a closed shape).
    const bandPath = (key) => {
      if (!cone) return "";
      const fwd = cone.map((c) => [xForDay(histSpan + c.d), yFor(c[key].upper)]);
      const back = [...cone].reverse().map((c) => [xForDay(histSpan + c.d), yFor(c[key].lower)]);
      return `${fmtPath([...fwd, ...back])} Z`;
    };
    const conePts = cone
      ? cone.filter((c) => c.d > 0).map((c) => ({ x: xForDay(histSpan + c.d), y: yFor(c.outer.upper), date: c.date, cone: c }))
      : [];

    const yTicks = [0, 1, 2, 3].map((i) => minV + (vRange * i) / 3);
    // At most ~6 history labels (3 when narrow), in days before the last point; the last one is its date.
    const labelEvery = Math.max(1, Math.ceil(histPts.length / (narrow ? 3 : 6)));
    const xLabels = histPts
      .map((p, i) => ({ x: p.x, label: i === histPts.length - 1 ? shortDate(lastDate) : `${daysApart(lastDate, p.date)}d`, i }))
      .filter((l) => l.i === histPts.length - 1 || ((histPts.length - 1 - l.i) % labelEvery === 0 && histPts.length - 1 - l.i >= labelEvery));
    const futureLabels = cone
      ? (narrow || futW < 160 ? [30] : [10, 20, 30]).map((d) => ({ x: xForDay(histSpan + d), label: `+${d}d` }))
      : [];
    // The cone's start label sits at the top of the divider: inside the future section when it has room, else left of it.
    const startLabel = cone && { text: startText(lastDate), right: futW >= 100 };

    return { W, H, PAD_L, PAD_R, PAD_T, plotH, linePath, areaPath, outerPath: bandPath("outer"), innerPath: bandPath("inner"),
      last, yTicks, yFor, xLabels, futureLabels, startLabel, histPts, conePts };
  }, [history, cone, layers, dims, startText]);

  const [hoverPt, setHoverPt] = useState(null);

  const handlePointerMove = (e) => {
    if (!chart) return;
    const rect = containerRef.current.getBoundingClientRect();
    const svgX = (e.clientX - rect.left) * (chart.W / rect.width);
    let closest = null;
    let minDiff = Infinity;
    [...chart.histPts, ...chart.conePts].forEach((pt) => {
      const diff = Math.abs(pt.x - svgX);
      if (diff < minDiff) {
        minDiff = diff;
        closest = pt;
      }
    });
    if (!closest) return setHoverPt(null);
    // Tooltip position in container pixels, computed here (not during render) from the container's size.
    const w = containerRef.current.clientWidth, h = containerRef.current.clientHeight;
    const left = Math.max(6, Math.min((closest.x / chart.W) * w - 70, w - (closest.cone ? 200 : 130)));
    const top = Math.max(6, (closest.y / chart.H) * h - 60);
    setHoverPt({ ...closest, left, top });
  };

  return (
    <div
      className="adt-chart-body"
      ref={containerRef}
      style={{ position: "relative", cursor: "crosshair", touchAction: "pan-y" }}
      onPointerMove={handlePointerMove}
      onPointerLeave={() => setHoverPt(null)}
    >
      {!chart ? (
        <div className="adt-chart-empty">{emptyText}</div>
      ) : (
        <>
          <svg width="100%" height="100%" viewBox={`0 0 ${chart.W} ${chart.H}`} style={{ overflow: "visible" }}
            data-layers={layers.join(" ")}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--sv2-accent)" stopOpacity="0.22" />
                <stop offset="100%" stopColor="var(--sv2-accent)" stopOpacity="0" />
              </linearGradient>
            </defs>

            {chart.yTicks.map((v, i) => {
              const y = chart.yFor(v);
              return (
                <g key={i}>
                  <line x1={chart.PAD_L} y1={y} x2={chart.W - chart.PAD_R} y2={y} stroke="var(--sv2-border)" strokeWidth="0.7" strokeDasharray="4,4" />
                  <text x={chart.PAD_L - 10} y={y + 4} fontSize="10.5" fill="var(--sv2-text-mute)" textAnchor="end">{formatAxis(v)}</text>
                </g>
              );
            })}

            {chart.xLabels.map((l, i) => (
              <text key={i} x={l.x} y={chart.H - 8} fontSize="10" fill="var(--sv2-text-mute)" textAnchor="middle">{l.label}</text>
            ))}
            {chart.futureLabels.map((l, i) => (
              <text key={`f${i}`} x={l.x} y={chart.H - 8} fontSize="10" fill="var(--sv2-text-mute)" textAnchor="middle">{l.label}</text>
            ))}

            {layers.includes("cone-outer") && (
              <line x1={chart.last.x} y1={chart.PAD_T} x2={chart.last.x} y2={chart.PAD_T + chart.plotH} stroke="var(--sv2-border-strong)" strokeWidth="1" strokeDasharray="3,3" />
            )}
            {layers.includes("cone-outer") && <path d={chart.outerPath} fill="var(--sv2-accent)" opacity="0.14" data-layer="cone-outer" />}
            {layers.includes("cone-inner") && <path d={chart.innerPath} fill="var(--sv2-accent)" opacity="0.22" data-layer="cone-inner" />}

            <path d={chart.areaPath} fill={`url(#${gradientId})`} />
            <path d={chart.linePath} fill="none" stroke="var(--sv2-accent)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" data-layer="history" />

            {chart.startLabel && (
              <g>
                <circle cx={chart.last.x} cy={chart.last.y} r="3.5" fill="var(--sv2-accent)" stroke="var(--sv2-card)" strokeWidth="1.5" />
                <text x={chart.last.x + (chart.startLabel.right ? 6 : -6)} y={chart.PAD_T + 10} fontSize="10.5"
                  fill="var(--sv2-text-mute)" textAnchor={chart.startLabel.right ? "start" : "end"} data-role="cone-start">
                  {chart.startLabel.text}
                </text>
              </g>
            )}

            {hoverPt && (
              <g>
                <line x1={hoverPt.x} y1={chart.PAD_T} x2={hoverPt.x} y2={chart.H - 24} stroke="var(--sv2-accent)" strokeWidth="1" strokeDasharray="3,3" opacity="0.75" />
                {!hoverPt.cone && (
                  <>
                    <circle cx={hoverPt.x} cy={hoverPt.y} r="7" fill="var(--sv2-accent)" opacity="0.25" />
                    <circle cx={hoverPt.x} cy={hoverPt.y} r="4" fill="var(--sv2-accent)" stroke="#fff" strokeWidth="2" />
                  </>
                )}
              </g>
            )}
          </svg>

          {hoverPt && (
            <div
              style={{
                position: "absolute",
                left: hoverPt.left,
                top: hoverPt.top,
                background: "var(--sv2-card)",
                border: "1px solid var(--sv2-border)",
                borderRadius: 8,
                padding: "5px 9px",
                boxShadow: "0 4px 12px rgba(0,0,0,0.25)",
                pointerEvents: "none",
                zIndex: 20,
                whiteSpace: "nowrap",
              }}
            >
              <div style={{ fontSize: 10, color: "var(--sv2-text-mute)", fontWeight: 600 }}>{hoverPt.date}</div>
              {hoverPt.cone ? (
                <>
                  <div style={{ fontSize: 11.5, color: "var(--sv2-text)" }}>
                    50% range: <b>{formatValue(hoverPt.cone.inner.lower)}–{formatValue(hoverPt.cone.inner.upper)}</b>
                  </div>
                  <div style={{ fontSize: 11.5, color: "var(--sv2-text)" }}>
                    80% range: <b>{formatValue(hoverPt.cone.outer.lower)}–{formatValue(hoverPt.cone.outer.upper)}</b>
                  </div>
                </>
              ) : (
                <div style={{ fontSize: 12.5, color: "var(--sv2-text)", fontWeight: 800 }}>{formatValue(hoverPt.price)}</div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
