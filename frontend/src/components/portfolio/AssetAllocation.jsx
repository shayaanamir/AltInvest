import { useState, useEffect } from "react";
import { useTheme } from "../../context/ThemeContext";
import { sv2Colors } from "../../utils/sv2Colors";
import { portfolioApi } from "../../services/portfolioApi";

const CATEGORY_COLOR_KEY = {
  Crypto: "accent",
  NFTs: "green",
  RWA: "red",
  Commodities: "greyArc",
};

function DonutChart({ data, colors, track }) {
  const cx = 80, cy = 80, r = 60, stroke = 22;
  const circumference = 2 * Math.PI * r;
  let offset = 0;

  return (
    <svg width="160" height="160" viewBox="0 0 160 160">
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={track} strokeWidth={stroke} />
      {data.map((seg) => {
        const dash = (seg.pct / 100) * circumference;
        const gap = circumference - dash;
        const segOffset = offset;
        offset += dash;
        const color = colors[CATEGORY_COLOR_KEY[seg.label] || "accent"];
        return (
          <circle
            key={seg.label}
            cx={cx} cy={cy} r={r}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeDasharray={`${dash} ${gap}`}
            strokeDashoffset={-segOffset + circumference * 0.25}
            style={{ transform: "rotate(-90deg)", transformOrigin: "80px 80px" }}
          />
        );
      })}
    </svg>
  );
}

export default function AssetAllocation() {
  const { isDark } = useTheme();
  const colors = isDark ? sv2Colors.dark : sv2Colors.light;
  const [allocation, setAllocation] = useState(null);

  useEffect(() => {
    portfolioApi.getAllocation().then(setAllocation).catch(console.error);
  }, []);

  return (
    <div className="sv2-card sv2-card-pad">
      <div className="sv2-card-title">Asset allocation</div>
      <div className="sv2-card-sub" style={{ marginBottom: 16 }}>By category</div>

      {!allocation ? (
        <div className="sv2-muted sv2-small" style={{ padding: "24px 0" }}>Loading…</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
          <DonutChart data={allocation} colors={colors} track={colors.greyArc} />
          <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: 7 }}>
            {allocation.map((a) => (
              <div key={a.label} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                  <span
                    style={{ width: 8, height: 8, borderRadius: "50%", background: colors[CATEGORY_COLOR_KEY[a.label] || "accent"], flexShrink: 0 }}
                  />
                  <span className="sv2-small sv2-muted">{a.label}</span>
                </div>
                <span className="sv2-small sv2-bold">{a.pct.toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}