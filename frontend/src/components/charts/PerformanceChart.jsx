import { useState, useEffect, useRef } from "react";
import { useTheme } from "../../context/ThemeContext";
import { TIME_FILTERS } from "../../data/constants";
import { makeStyles } from "../../styles/makeStyles";
import { dashboardApi } from "../../services/dashboardApi";

export default function PerformanceChart() {
  const { tokens: t } = useTheme();
  const s = makeStyles(t);
  const [activeFilter, setActiveFilter] = useState("1M");
  
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const containerRef = useRef(null);
  const [dims, setDims] = useState({ W: 500, H: 200 });

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
    dashboardApi.getPerformanceData(activeFilter).then(res => {
      setData(res);
      setLoading(false);
    }).catch(console.error);
  }, [activeFilter]);

  const { W, H } = dims;
  let content = null;

  if (loading) {
    content = <div style={{ height: H, display: "flex", alignItems: "center", justifyContent: "center", color: t.textMuted }}>Loading chart...</div>;
  } else if (data.length < 2) {
    content = <div style={{ height: H, display: "flex", alignItems: "center", justifyContent: "center", color: t.textMuted }}>Not enough data</div>;
  } else {
    const vals = data.map(d => d.value);
    const minVal = Math.min(...vals) * 0.98; // small padding
    const maxVal = Math.max(...vals) * 1.02; // small padding
    const range = maxVal - minVal;
    
    // Generate 4 Y-axis labels
    const yLabels = [];
    for (let i = 0; i < 4; i++) {
      yLabels.push(minVal + (range * i) / 3);
    }
    
    // Generate X-axis labels based on dates
    const xLabels = [];
    if (data.length > 0) xLabels.push(data[0].date);
    if (data.length > 2) xLabels.push(data[Math.floor(data.length / 2)].date);
    if (data.length > 1) xLabels.push(data[data.length - 1].date);
    
    const toPoint = (v, i, total) => {
      // Pad 45px left for text, 15px right
      const x = 45 + (i / (total - 1)) * (W - 60);
      const y = H - 25 - ((v - minVal) / range) * (H - 40);
      return { x, y };
    };

    const pts = data.map((d, i) => toPoint(d.value, i, data.length));
    const last = pts[pts.length - 1];
    const linePath = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
    const areaPath = `M ${pts[0].x} ${pts[0].y} ${pts.map(p => `L ${p.x} ${p.y}`).join(" ")} L ${last.x} ${H - 25} L ${pts[0].x} ${H - 25} Z`;

    content = (
      <svg width="100%" height="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: "block" }}>
        <defs>
          <linearGradient id="perfGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={t.accentTeal} stopOpacity="0.22" />
            <stop offset="100%" stopColor={t.accentTeal} stopOpacity="0.01" />
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
            <text key={i} x={x} y={H - 5} fontSize="9.5" fill={t.textMuted} textAnchor="middle">{lb.substring(5)}</text>
          );
        })}

        <path d={areaPath} fill="url(#perfGrad)" />
        <path d={linePath} fill="none" stroke={t.accentTeal} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx={last.x} cy={last.y} r="4" fill={t.accentTeal} />
        <circle cx={last.x} cy={last.y} r="7" fill={t.accentTeal} fillOpacity="0.18" />
      </svg>
    );
  }

  return (
    <div style={{ ...s.card, display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={s.cardHeader}>
        <div style={{ display: "flex", alignItems: "center" }}>
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

      <div style={{ flex: 1, position: "relative", minHeight: 200, margin: "10px" }}>
        <div ref={containerRef} style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0 }}>
          {content}
        </div>
      </div>
    </div>
  );
}
