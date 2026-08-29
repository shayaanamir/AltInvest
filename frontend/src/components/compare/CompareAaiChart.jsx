import { useState, useRef } from "react";
import { CMP_PALETTE } from "./chartPalette.js";

export default function CompareAaiChart({ assets }) {
  const [hoveredIdx, setHoveredIdx] = useState(null);
  const containerRef = useRef(null);

  const W = 640;
  const H = 260;
  const padLeft = 40;
  const padBottom = 30;
  const padTop = 10;
  const chartH = H - padTop - padBottom;
  const barWidth = Math.min(64, Math.max(36, Math.floor((W - padLeft - 40) / (assets.length * 1.8))));
  const gap = (W - padLeft - 20 - barWidth * assets.length) / (assets.length + 1);

  const handleMouseMove = (e) => {
    if (!containerRef.current || !assets?.length) return;
    const rect = containerRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const svgX = (mouseX / rect.width) * W;

    let closest = 0;
    let minDiff = Infinity;
    assets.forEach((_, i) => {
      const barX = padLeft + gap + i * (barWidth + gap) + barWidth / 2;
      const diff = Math.abs(barX - svgX);
      if (diff < minDiff) {
        minDiff = diff;
        closest = i;
      }
    });
    setHoveredIdx(closest);
  };

  const activeAsset = hoveredIdx != null ? assets[hoveredIdx] : null;
  const activeX = hoveredIdx != null ? padLeft + gap + hoveredIdx * (barWidth + gap) + barWidth / 2 : 0;
  const activeY = activeAsset ? padTop + chartH - ((activeAsset.aaiScore ?? 0) / 100) * chartH : 0;

  return (
    <div className="cmp-card cmp-chart-card" style={{ position: "relative" }}>
      <div className="cmp-chart-title">AAI score</div>
      <div className="cmp-chart-sub">Composite score, normalised across categories</div>
      
      <div
        ref={containerRef}
        style={{ position: "relative", cursor: "crosshair" }}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoveredIdx(null)}
      >
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
            const isHovered = hoveredIdx === i;
            return (
              <g key={a.id}>
                <rect
                  x={x}
                  y={y}
                  width={barWidth}
                  height={Math.max(barH, 1)}
                  rx="6"
                  fill={CMP_PALETTE[i % CMP_PALETTE.length]}
                  opacity={isHovered ? 1 : 0.85}
                  stroke={isHovered ? "#fff" : "none"}
                  strokeWidth="2"
                />
                <text x={x + barWidth / 2} y={H - 8} fontSize="11" fontWeight="700" textAnchor="middle" fill="var(--sv2-text)">
                  {a.symbol}
                </text>
              </g>
            );
          })}
        </svg>

        {activeAsset && (
          <div
            style={{
              position: "absolute",
              left: Math.min(Math.max((activeX / W) * (containerRef.current?.clientWidth || W) - 60, 10), (containerRef.current?.clientWidth || W) - 130),
              top: Math.max(10, (activeY / H) * (containerRef.current?.clientHeight || H) - 52),
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
            <div style={{ fontSize: 13, color: CMP_PALETTE[hoveredIdx % CMP_PALETTE.length], fontWeight: 800 }}>
              AAI Score: {Math.round(activeAsset.aaiScore ?? 0)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}