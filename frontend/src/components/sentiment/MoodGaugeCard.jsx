import { polarToCartesian, describeArc } from "../../utils/svgArc";

// ── geometry constants (slightly smaller so 3 cards per row have room) ───────
const CX = 70;
const CY = 74;
const R  = 54;
const SW = 9;
const SEG = [
  [179, 102],
  [99,  81],
  [78,  1],
];
// ─────────────────────────────────────────────────────────────────────────────

export default function MoodGaugeCard({
  eyebrow,
  title,
  metaLine,
  caption,
  infoNote,
  axisLabels,
  score,
  arcGreen,
  arcRed,
  greyArc,
}) {
  const pct         = Math.max(0, Math.min(100, (score + 100) / 2));
  const needleAngle = 180 - (pct / 100) * 180;
  const needleLen   = R - 12;
  const tip         = polarToCartesian(CX, CY, needleLen, needleAngle);

  const VIEW_TOP = 14;
  const SVG_W = 142;
  const SVG_H = CY + Math.ceil(SW / 2) + 2;
  const VIEW_H = SVG_H - VIEW_TOP;

  return (
    <div className="sv2-card sv2-gauge-card">
      <div className="sv2-gauge-inner">

        {/* ── gauge + axis labels ─────────────────────────────────── */}
        <div className="sv2-gauge-col">
          <svg
            width={SVG_W}
            viewBox={`0 ${VIEW_TOP} ${SVG_W} ${VIEW_H}`}
            style={{ display: "block", overflow: "visible" }}
          >
            <path d={describeArc(CX, CY, R, ...SEG[0])} stroke={arcRed}   strokeWidth={SW} fill="none" strokeLinecap="butt" />
            <path d={describeArc(CX, CY, R, ...SEG[1])} stroke={greyArc}  strokeWidth={SW} fill="none" strokeLinecap="butt" />
            <path d={describeArc(CX, CY, R, ...SEG[2])} stroke={arcGreen} strokeWidth={SW} fill="none" strokeLinecap="butt" />
            <line x1={CX} y1={CY} x2={tip.x} y2={tip.y} stroke="#9ea5be" strokeWidth="2" strokeLinecap="round" />
            <circle cx={CX} cy={CY} r="4" fill="#9ea5be" />
          </svg>

          <div className="sv2-gauge-axis-row">
            <span>{axisLabels[0]}</span>
            <span>{axisLabels[1]}</span>
            <span>{axisLabels[2]}</span>
          </div>
        </div>

        {/* ── text content — flexible, wraps instead of overflowing ── */}
        <div className="sv2-gauge-text">
          <div className="sv2-gauge-eyebrow">{eyebrow}</div>
          <div className="sv2-gauge-title2">{title}</div>
          <div className="sv2-gauge-meta2">{metaLine}</div>
          {caption && <div className="sv2-gauge-caption2">{caption}</div>}
        </div>
      </div>
    </div>
  );
}