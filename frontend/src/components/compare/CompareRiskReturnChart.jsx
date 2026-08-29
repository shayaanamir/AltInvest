import { useState, useRef } from "react";
import { CMP_PALETTE } from "./chartPalette";

export default function CompareRiskReturnChart({ assets }) {
  const [hoveredIdx, setHoveredIdx] = useState(null);
  const containerRef = useRef(null);

  const W = 640;
  const H = 260;
  const padLeft = 40;
  const padRight = 20;
  const padTop = 10;
  const padBottom = 30;
  const chartW = W - padLeft - padRight;
  const chartH = H - padTop - padBottom;

  const xs = assets.map((a) => a.volatility ?? 0);
  const ys = assets.map((a) => a.expectedReturn ?? 0);
  const xMin = 0;
  const xMax = Math.max(100, ...xs);
  const yMin = Math.min(0, ...ys) - 5;
  const yMax = Math.max(10, ...ys) + 5;

  const toX = (v) => padLeft + ((v - xMin) / (xMax - xMin)) * chartW;
  const toY = (v) => padTop + chartH - ((v - yMin) / (yMax - yMin)) * chartH;

  const yTicks = [];
  for (let i = 0; i <= 4; i++) yTicks.push(Math.round(yMin + ((yMax - yMin) * i) / 4));

  const handleMouseMove = (e) => {
    if (!containerRef.current || !assets?.length) return;
    const rect = containerRef.current.getBoundingClientRect();
    const mouseX = ((e.clientX - rect.left) / rect.width) * W;
    const mouseY = ((e.clientY - rect.top) / rect.height) * H;

    let closest = 0;
    let minDist = Infinity;
    assets.forEach((a, i) => {
      const px = toX(a.volatility ?? 0);
      const py = toY(a.expectedReturn ?? 0);
      const dist = Math.hypot(px - mouseX, py - mouseY);
      if (dist < minDist) {
        minDist = dist;
        closest = i;
      }
    });
    setHoveredIdx(closest);
  };

  const activeAsset = hoveredIdx != null ? assets[hoveredIdx] : null;
  const activeX = activeAsset ? toX(activeAsset.volatility ?? 0) : 0;
  const activeY = activeAsset ? toY(activeAsset.expectedReturn ?? 0) : 0;

  return (
    <div className="cmp-card cmp-chart-card" style={{ position: "relative" }}>
      <div className="cmp-chart-title">Risk vs expected return</div>
      <div className="cmp-chart-sub">Volatility on X, model-implied return on Y</div>
      
      <div
        ref={containerRef}
        style={{ position: "relative", cursor: "crosshair" }}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoveredIdx(null)}
      >
        <svg width="100%" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet">
          {yTicks.map((v) => {
            const y = toY(v);
            return (
              <g key={v}>
                <line x1={padLeft} y1={y} x2={W - padRight} y2={y} stroke="var(--sv2-border)" strokeDasharray="4,4" />
                <text x={padLeft - 8} y={y + 4} fontSize="10" textAnchor="end" fill="var(--sv2-text-mute)">
                  {v}%
                </text>
              </g>
            );
          })}

          {activeAsset && (
            <g>
              <line x1={activeX} y1={padTop} x2={activeX} y2={H - padBottom} stroke={CMP_PALETTE[hoveredIdx % CMP_PALETTE.length]} strokeWidth="1" strokeDasharray="3,3" opacity="0.6" />
              <line x1={padLeft} y1={activeY} x2={W - padRight} y2={activeY} stroke={CMP_PALETTE[hoveredIdx % CMP_PALETTE.length]} strokeWidth="1" strokeDasharray="3,3" opacity="0.6" />
            </g>
          )}

          {assets.map((a, i) => {
            const x = toX(a.volatility ?? 0);
            const y = toY(a.expectedReturn ?? 0);
            const isHovered = hoveredIdx === i;
            return (
              <g key={a.id}>
                {isHovered && <circle cx={x} cy={y} r="11" fill={CMP_PALETTE[i % CMP_PALETTE.length]} opacity="0.3" />}
                <circle cx={x} cy={y} r={isHovered ? 8 : 6.5} fill={CMP_PALETTE[i % CMP_PALETTE.length]} stroke="#fff" strokeWidth="1.5" />
                <text x={x} y={H - 8} fontSize="10" fontWeight={isHovered ? "700" : "400"} textAnchor="middle" fill="var(--sv2-text-mute)">
                  {Math.round(a.volatility ?? 0)}%
                </text>
              </g>
            );
          })}
        </svg>

        {activeAsset && (
          <div
            style={{
              position: "absolute",
              left: Math.min(Math.max((activeX / W) * (containerRef.current?.clientWidth || W) - 70, 10), (containerRef.current?.clientWidth || W) - 150),
              top: Math.max(10, (activeY / H) * (containerRef.current?.clientHeight || H) - 56),
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
            <div style={{ fontSize: 10.5, color: "var(--sv2-text-mute)", fontWeight: 600 }}>
              {activeAsset.name} ({activeAsset.symbol})
            </div>
            <div style={{ fontSize: 12, color: CMP_PALETTE[hoveredIdx % CMP_PALETTE.length], fontWeight: 800 }}>
              Volatility (X): {Math.round(activeAsset.volatility ?? 0)}% · Return (Y): {activeAsset.expectedReturn > 0 ? "+" : ""}{activeAsset.expectedReturn}%
            </div>
          </div>
        )}
      </div>

      <div className="cmp-legend-row" style={{ marginTop: 10 }}>
        {assets.map((a, i) => (
          <span key={a.id} className="cmp-legend-item" style={{ opacity: hoveredIdx == null || hoveredIdx === i ? 1 : 0.4 }}>
            <span className="cmp-legend-dot" style={{ background: CMP_PALETTE[i % CMP_PALETTE.length] }} />
            {a.symbol}
          </span>
        ))}
      </div>
    </div>
  );
}