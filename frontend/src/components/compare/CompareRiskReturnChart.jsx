import { CMP_PALETTE } from "./chartPalette";

export default function CompareRiskReturnChart({ assets }) {
  const W = 640;
  const H = 260;
  const padLeft = 40;
  const padRight = 20;
  const padTop = 10;
  const padBottom = 30;
  const chartW = W - padLeft - padRight;
  const chartH = H - padTop - padBottom;

  const xs = assets.map((a) => a.volatility);
  const ys = assets.map((a) => a.expectedReturn);
  const xMin = 0;
  const xMax = Math.max(100, ...xs);
  const yMin = Math.min(0, ...ys) - 5;
  const yMax = Math.max(10, ...ys) + 5;

  const toX = (v) => padLeft + ((v - xMin) / (xMax - xMin)) * chartW;
  const toY = (v) => padTop + chartH - ((v - yMin) / (yMax - yMin)) * chartH;

  const yTicks = [];
  for (let i = 0; i <= 4; i++) yTicks.push(Math.round(yMin + ((yMax - yMin) * i) / 4));

  return (
    <div className="cmp-card cmp-chart-card">
      <div className="cmp-chart-title">Risk vs expected return</div>
      <div className="cmp-chart-sub">Volatility on X, model-implied return on Y</div>
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet">
        {yTicks.map((v) => {
          const y = toY(v);
          return (
            <g key={v}>
              <line x1={padLeft} y1={y} x2={W - padRight} y2={y} stroke="var(--sv2-border)" strokeDasharray="4,4" />
              <text x={padLeft - 8} y={y + 4} fontSize="10" textAnchor="end" fill="var(--sv2-text-mute)">
                {v}
              </text>
            </g>
          );
        })}
        {assets.map((a, i) => {
          const x = toX(a.volatility);
          const y = toY(a.expectedReturn);
          return (
            <g key={a.id}>
              <circle cx={x} cy={y} r="7" fill={CMP_PALETTE[i % CMP_PALETTE.length]} />
              <text x={x} y={H - 8} fontSize="10" textAnchor="middle" fill="var(--sv2-text-mute)">
                {Math.round(a.volatility)}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="cmp-legend-row">
        {assets.map((a, i) => (
          <span key={a.id} className="cmp-legend-item">
            <span className="cmp-legend-dot" style={{ background: CMP_PALETTE[i % CMP_PALETTE.length] }} />
            {a.symbol}
          </span>
        ))}
      </div>
    </div>
  );
}