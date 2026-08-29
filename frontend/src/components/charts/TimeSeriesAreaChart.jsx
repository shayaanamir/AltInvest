import { useMemo, useState, useRef } from "react";

export function buildSeriesPaths(data, width, height, { padLeft = 0, padRight = 0, padTop = 0, padBottom = 0 } = {}) {
  if (!data || data.length < 2) return null;
  const vals = data.map((d) => (typeof d === "number" ? d : d.value));
  const minV = Math.min(...vals) * 0.98;
  const maxV = Math.max(...vals) * 1.02;
  const range = Math.max(1, maxV - minV);

  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  const pts = data.map((d, i) => {
    const v = typeof d === "number" ? d : d.value;
    return {
      x: padLeft + (i / (data.length - 1)) * plotW,
      y: height - padBottom - ((v - minV) / range) * plotH,
    };
  });
  const last = pts[pts.length - 1];
  const linePath = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
  const areaPath = `${linePath} L ${last.x.toFixed(1)} ${height - padBottom} L ${pts[0].x.toFixed(1)} ${height - padBottom} Z`;

  return { pts, last, linePath, areaPath, minV, maxV, range };
}

function defaultXFormatter(dateStr) {
  if (!dateStr) return "";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    if (dateStr.includes("T")) {
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
    }
    return d.toLocaleDateString([], { month: "short", day: "numeric" });
  } catch {
    return dateStr;
  }
}

export default function TimeSeriesAreaChart({
  data,                 // [{ date, value }]
  width = 560,
  height = 240,
  color = "var(--sv2-accent)",
  padLeft = 52,
  padRight = 18,
  padTop = 22,
  padBottom = 26,
  yLabelFormatter = (v) => (v >= 1000 ? `$${(v / 1000).toFixed(1)}K` : `$${v.toFixed(0)}`),
  xLabelFormatter,       // optional (date, index) => string
  showDots = true,
  gradientId = "tsa-grad",
}) {
  const [hoverIdx, setHoverIdx] = useState(null);
  const containerRef = useRef(null);

  const chart = useMemo(() => {
    const res = buildSeriesPaths(data, width, height, { padLeft, padRight, padTop, padBottom });
    if (!res) return null;

    const yTicks = [0, 1, 2, 3].map((i) => res.minV + (res.range * i) / 3);

    // Pick 4 to 5 evenly spaced indices for X axis ticks
    const n = data.length;
    const count = Math.min(5, Math.max(3, Math.floor(n / 2)));
    const xIdxs = Array.from({ length: count }, (_, i) => Math.round((i / (count - 1)) * (n - 1)));

    return { ...res, yTicks, xIdxs };
  }, [data, width, height, padLeft, padRight, padTop, padBottom]);

  if (!chart) {
    return (
      <div className="sv2-muted sv2-small" style={{ height, display: "flex", alignItems: "center", justifyContent: "center" }}>
        Not enough data
      </div>
    );
  }

  const formatX = xLabelFormatter || defaultXFormatter;

  const handleMouseMove = (e) => {
    if (!containerRef.current || !data?.length) return;
    const rect = containerRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const scaleX = width / rect.width;
    const svgX = mouseX * scaleX;

    // Find closest point by X coordinate
    let closestIdx = 0;
    let minDiff = Infinity;
    chart.pts.forEach((pt, i) => {
      const diff = Math.abs(pt.x - svgX);
      if (diff < minDiff) {
        minDiff = diff;
        closestIdx = i;
      }
    });

    setHoverIdx(closestIdx);
  };

  const handleMouseLeave = () => {
    setHoverIdx(null);
  };

  const activeIdx = hoverIdx;
  const activePt = activeIdx != null ? chart.pts[activeIdx] : null;
  const activeDataItem = activeIdx != null ? data[activeIdx] : null;

  return (
    <div
      ref={containerRef}
      style={{ position: "relative", width: "100%", height, cursor: "crosshair" }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      <svg
        width="100%"
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        style={{ display: "block" }}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.28" />
            <stop offset="100%" stopColor={color} stopOpacity="0.01" />
          </linearGradient>
        </defs>

        {/* Y Grid Lines & Labels */}
        {chart.yTicks.map((v, i) => {
          const y = height - padBottom - ((v - chart.minV) / Math.max(1, chart.range)) * (height - padTop - padBottom);
          return (
            <g key={i}>
              <line
                x1={padLeft}
                y1={y}
                x2={width - padRight}
                y2={y}
                stroke="var(--sv2-border)"
                strokeWidth="1"
                strokeDasharray="4 4"
              />
              <text
                x={padLeft - 8}
                y={y + 3.5}
                fontSize="10"
                fontWeight="500"
                fill="var(--sv2-text-mute)"
                textAnchor="end"
              >
                {yLabelFormatter(v)}
              </text>
            </g>
          );
        })}

        {/* X Axis Labels */}
        {chart.xIdxs.map((idx) => {
          const pt = chart.pts[idx];
          if (!pt) return null;
          const label = formatX(data[idx]?.date, idx);
          return (
            <text
              key={idx}
              x={pt.x}
              y={height - 6}
              fontSize="10.5"
              fontWeight="500"
              fill="var(--sv2-text-mute)"
              textAnchor="middle"
            >
              {label}
            </text>
          );
        })}

        {/* Area & Line Paths */}
        <path d={chart.areaPath} fill={`url(#${gradientId})`} />
        <path
          d={chart.linePath}
          fill="none"
          stroke={color}
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* End dot when not hovering */}
        {showDots && activeIdx == null && (
          <circle cx={chart.last.x} cy={chart.last.y} r="4.5" fill={color} stroke="#fff" strokeWidth="1.5" />
        )}

        {/* Hover Crosshair Line & Point Highlight */}
        {activePt && (
          <g>
            <line
              x1={activePt.x}
              y1={padTop}
              x2={activePt.x}
              y2={height - padBottom}
              stroke={color}
              strokeWidth="1"
              strokeDasharray="3 3"
              opacity="0.75"
            />
            <circle cx={activePt.x} cy={activePt.y} r="7" fill={color} opacity="0.25" />
            <circle cx={activePt.x} cy={activePt.y} r="4" fill={color} stroke="#fff" strokeWidth="2" />
          </g>
        )}
      </svg>

      {/* Floating Hover Tooltip Box */}
      {activePt && activeDataItem && (
        <div
          style={{
            position: "absolute",
            left: Math.min(Math.max(activePt.x * (containerRef.current ? containerRef.current.clientWidth / width : 1) - 60, 10), (containerRef.current?.clientWidth || width) - 130),
            top: Math.max(10, activePt.y * (containerRef.current ? containerRef.current.clientHeight / height : 1) - 52),
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
          <div style={{ fontSize: 10, color: "var(--sv2-text-mute)", fontWeight: 600 }}>
            {formatX(activeDataItem.date)}
          </div>
          <div style={{ fontSize: 12.5, color: "var(--sv2-text)", fontWeight: 800 }}>
            {typeof activeDataItem.value === "number" ? `$${activeDataItem.value.toLocaleString()}` : activeDataItem.value}
          </div>
        </div>
      )}
    </div>
  );
}