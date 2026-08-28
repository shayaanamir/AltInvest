import { CMP_PALETTE } from "./chartPalette.js";

export default function CompareAaiChart({ assets }) {
  const W = 640;
  const H = 260;
  const padLeft = 40;
  const padBottom = 30;
  const padTop = 10;
  const chartH = H - padTop - padBottom;
  const barWidth = 64;
  const gap = (W - padLeft - 20 - barWidth * assets.length) / (assets.length + 1);

  return (
    <div className="cmp-card cmp-chart-card">
      <div className="cmp-chart-title">AAI score</div>
      <div className="cmp-chart-sub">Composite score, normalised across categories</div>
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet">
        {[0, 25, 50, 75, 100].map((v) => {
          const y = padTop + chartH - (v / 100) * chartH;
          return (
            <g key={v}>
              <line x1={padLeft} y1={y} x2={W - 10} y2={y} stroke="var(--sv2-border)" strokeDasharray="4,4" />
              <text x={padLeft - 10} y={y + 4} fontSize="10" textAnchor="end" fill="var(--sv2-text-mute)">
                {v}
              </text>
            </g>
          );
        })}
        {assets.map((a, i) => {
          const x = padLeft + gap + i * (barWidth + gap);
          const score = a.aaiScore ?? 0;
          const barH = (score / 100) * chartH;
          const y = padTop + chartH - barH;
          return (
            <g key={a.id}>
              <rect x={x} y={y} width={barWidth} height={Math.max(barH, 1)} rx="6" fill={CMP_PALETTE[i % CMP_PALETTE.length]} />
              <text x={x + barWidth / 2} y={H - 8} fontSize="11" fontWeight="700" textAnchor="middle" fill="var(--sv2-text)">
                {a.symbol}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}