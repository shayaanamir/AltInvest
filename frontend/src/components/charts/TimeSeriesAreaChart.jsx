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

export default function TimeSeriesAreaChart({
  data,                 // [{ date, value }]
  width = 560,
  height = 220,
  color = "var(--sv2-accent)",
  padLeft = 46,
  padRight = 10,
  padTop = 10,
  padBottom = 22,
  yLabelFormatter = (v) => (v >= 1000 ? `$${(v / 1000).toFixed(1)}K` : `$${v.toFixed(0)}`),
  xLabelFormatter,       // optional (date, index) => string
  showDots = true,
  gradientId = "tsa-grad",
}) {
  const chart = useMemo(() => {
    const res = buildSeriesPaths(data, width, height, { padLeft, padRight, padTop, padBottom });
    if (!res) return null;

    const yTicks = [0, 1, 2, 3].map((i) => res.minV + (res.range * i) / 3);
    const xIdxs = [0, Math.floor((data.length - 1) / 2), data.length - 1];

    return { ...res, yTicks, xIdxs };
  }, [data, width, height, padLeft, padRight, padTop, padBottom]);

  if (!chart) {
    return (
      <div className="sv2-muted sv2-small" style={{ height, display: "flex", alignItems: "center", justifyContent: "center" }}>
        Not enough data
      </div>
    );
  }

  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.28" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>

      {chart.yTicks.map((v, i) => {
        const y = height - padBottom - ((v - chart.yTicks[0]) / Math.max(1, chart.yTicks[3] - chart.yTicks[0])) * (height - padTop - padBottom);
        return (
          <g key={i}>
            <line x1={padLeft} y1={y} x2={width - padRight} y2={y} stroke="var(--sv2-grey-arc)" strokeWidth="0.7" strokeDasharray="4,4" />
            <text x={padLeft - 8} y={y + 4} fontSize="9.5" fill="var(--sv2-grey-arc)" textAnchor="end">{yLabelFormatter(v)}</text>
          </g>
        );
      })}

      {xLabelFormatter && chart.xIdxs.map((idx, i) => (
        <text key={i} x={chart.pts[idx].x} y={height - 5} fontSize="9.5" fill="var(--sv2-grey-arc)" textAnchor="middle">
          {xLabelFormatter(data[idx].date, idx)}
        </text>
      ))}

      <path d={chart.areaPath} fill={`url(#${gradientId})`} />
      <path d={chart.linePath} fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
      {showDots && <circle cx={chart.last.x} cy={chart.last.y} r="4" fill={color} />}
    </svg>
  );
}