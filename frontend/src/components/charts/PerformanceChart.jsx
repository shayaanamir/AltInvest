import { useState } from "react";
import { useTheme } from "../../context/ThemeContext";
import { PERFORMANCE_DATA, TIME_FILTERS } from "../../data/constants";
import { makeStyles } from "../../styles/makeStyles";

const W = 530, H = 200, MIN_VAL = 30, MAX_VAL = 135;
const RANGE = MAX_VAL - MIN_VAL;
const Y_LABELS = [40, 60, 80, 100, 120];
const X_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"];

function toPoint(v, i, total) {
  const x = 28 + (i / (total - 1)) * (W - 36);
  const y = H - 20 - ((v - MIN_VAL) / RANGE) * (H - 40);
  return { x, y };
}

export default function PerformanceChart() {
  const { tokens: t } = useTheme();
  const s = makeStyles(t);
  const [activeFilter, setActiveFilter] = useState("1M");

  const pts      = PERFORMANCE_DATA.map((v, i) => toPoint(v, i, PERFORMANCE_DATA.length));
  const last     = pts[pts.length - 1];
  const linePath = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
  const areaPath = `M ${pts[0].x} ${pts[0].y} ${pts.map(p => `L ${p.x} ${p.y}`).join(" ")} L ${last.x} ${H - 20} L ${pts[0].x} ${H - 20} Z`;

  return (
    <div style={s.card}>
      <div style={s.cardHeader}>
        <div style={{ display: "flex", alignItems: "center" }}>
          <span style={{ color: t.accentTeal, marginRight: 6, fontSize: 13 }}>⚡</span>
          <span style={s.cardTitle}>Portfolio Performance</span>
        </div>
        <div style={s.timeFilters}>
          {TIME_FILTERS.map((f) => (
            <button
              key={f}
              style={{ ...s.timeBtn, ...(f === activeFilter ? s.timeBtnActive : {}) }}
              onClick={() => setActiveFilter(f)}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div style={{ padding: "6px 8px 8px" }}>
        <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} style={{ display: "block" }}>
          <defs>
            <linearGradient id="perfGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"   stopColor={t.accentTeal} stopOpacity="0.22" />
              <stop offset="100%" stopColor={t.accentTeal} stopOpacity="0.01" />
            </linearGradient>
          </defs>

          {Y_LABELS.map((v) => {
            const y = H - 20 - ((v - MIN_VAL) / RANGE) * (H - 40);
            return (
              <g key={v}>
                <line x1={28} y1={y} x2={W - 8} y2={y} stroke={t.border} strokeWidth="0.7" strokeDasharray="4,4" />
                <text x={22} y={y + 4} fontSize="9.5" fill={t.textMuted} textAnchor="end">{v}k</text>
              </g>
            );
          })}

          {X_LABELS.map((lb, i) => {
            const x = 28 + (i / (X_LABELS.length - 1)) * (W - 36);
            return (
              <text key={lb} x={x} y={H - 4} fontSize="9.5" fill={t.textMuted} textAnchor="middle">{lb}</text>
            );
          })}

          <path d={areaPath} fill="url(#perfGrad)" />
          <path d={linePath} fill="none" stroke={t.accentTeal} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          <circle cx={last.x} cy={last.y} r="4"  fill={t.accentTeal} />
          <circle cx={last.x} cy={last.y} r="7"  fill={t.accentTeal} fillOpacity="0.18" />
        </svg>
      </div>
    </div>
  );
}
