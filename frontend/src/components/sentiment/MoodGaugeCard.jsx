function polarToCartesian(cx, cy, r, angleDeg) {
  const rad = (angleDeg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy - r * Math.sin(rad) };
}

function describeArc(cx, cy, r, startAngle, endAngle) {
  const start = polarToCartesian(cx, cy, r, startAngle);
  const end   = polarToCartesian(cx, cy, r, endAngle);
  const large = Math.abs(startAngle - endAngle) <= 180 ? "0" : "1";
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${large} 1 ${end.x} ${end.y}`;
}

// ── geometry constants ────────────────────────────────────────────────────────
const CX = 87;   // pivot x
const CY = 90;   // pivot y  (sits just above SVG bottom edge)
const R  = 66;   // arc radius
const SW = 11;   // stroke width
// Arc angle boundaries — small angular gaps between segments produce
// the visible notch separating each section.
const SEG = [
  [179, 123],   // red   / bearish  segment
  [119, 61],    // grey  / neutral  segment
  [57,  1],     // teal  / bullish  segment
];
// ─────────────────────────────────────────────────────────────────────────────

export default function MoodGaugeCard({
  eyebrow,
  title,
  metaLine,
  caption,
  axisLabels,
  score,        // -100..100
  infoNote,
  arcGreen,     // muted teal  for the arc (NOT the same as UI green accent)
  arcRed,       // muted wine  for the arc
  greyArc,      // dark charcoal for the middle arc segment
}) {
  const pct         = Math.max(0, Math.min(100, (score + 100) / 2)); // → 0..100
  const needleAngle = 180 - (pct / 100) * 180;
  const needleLen   = R - 14;  // stops just before the arc
  const tip         = polarToCartesian(CX, CY, needleLen, needleAngle);

  // SVG height = CY + half-stroke so the pivot dot isn't clipped
  const SVG_W = 176;
  const SVG_H = CY + Math.ceil(SW / 2) + 2;  // = 98

  return (
    <div className="sv2-card" style={{ padding: "18px 22px 16px" }}>
      <div style={{ display: "flex", gap: 18, alignItems: "flex-start" }}>

        {/* ── LEFT: gauge + axis labels ─────────────────────────────────── */}
        <div style={{ flexShrink: 0 }}>
          <svg
            width={SVG_W} height={SVG_H}
            viewBox={`0 0 ${SVG_W} ${SVG_H}`}
            style={{ display: "block", overflow: "visible" }}
          >
            {/* Arc segments — butt caps for clean flat ends */}
            <path d={describeArc(CX, CY, R, ...SEG[0])} stroke={arcRed}   strokeWidth={SW} fill="none" strokeLinecap="butt" />
            <path d={describeArc(CX, CY, R, ...SEG[1])} stroke={greyArc}  strokeWidth={SW} fill="none" strokeLinecap="butt" />
            <path d={describeArc(CX, CY, R, ...SEG[2])} stroke={arcGreen} strokeWidth={SW} fill="none" strokeLinecap="butt" />

            {/* Needle */}
            <line
              x1={CX} y1={CY} x2={tip.x} y2={tip.y}
              stroke="#9ea5be"
              strokeWidth="2"
              strokeLinecap="round"
            />
            {/* Pivot dot */}
            <circle cx={CX} cy={CY} r="4.5" fill="#9ea5be" />
          </svg>

          {/* Axis labels — scoped to gauge width only */}
          <div style={{
            display: "flex",
            justifyContent: "space-between",
            width: SVG_W,
            marginTop: 5,
            paddingLeft: 1,
            paddingRight: 1,
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: "0.07em",
            textTransform: "uppercase",
            color: "var(--sv2-text-mute)",
          }}>
            <span>{axisLabels[0]}</span>
            <span>{axisLabels[1]}</span>
            <span>{axisLabels[2]}</span>
          </div>
        </div>

        {/* ── RIGHT: text content ───────────────────────────────────────── */}
        <div style={{ flex: 1, paddingTop: 4 }}>
          {/* Eyebrow */}
          <div style={{
            fontSize: 9.5,
            fontWeight: 700,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            color: "var(--sv2-text-mute)",
            marginBottom: 8,
          }}>
            {eyebrow}
          </div>

          {/* Title — always white in both modes */}
          <div style={{
            fontSize: 28,
            fontWeight: 800,
            letterSpacing: "-0.5px",
            color: "var(--sv2-text)",
            lineHeight: 1.1,
            marginBottom: 10,
          }}>
            {title}
          </div>

          {/* Meta line */}
          <div style={{
            fontSize: 12.5,
            color: "var(--sv2-text-soft)",
            lineHeight: 1.5,
            marginBottom: 5,
          }}>
            {metaLine}
          </div>

          {/* Caption */}
          {caption && (
            <div style={{
              fontSize: 10.5,
              color: "var(--sv2-text-mute)",
            }}>
              {caption}
            </div>
          )}
        </div>
      </div>

      {/* ── Info / warning note (NFT card) ─────────────────────────────── */}
      {infoNote && (
        <div style={{
          marginTop: 14,
          display: "flex",
          gap: 9,
          alignItems: "flex-start",
          background: "rgba(210, 145, 60, 0.1)",
          border: "1px solid rgba(210, 145, 60, 0.22)",
          borderRadius: 9,
          padding: "9px 13px",
          fontSize: 11,
          color: "var(--sv2-text-soft)",
          lineHeight: 1.45,
        }}>
          {/* Amber filled circle icon */}
          <span style={{
            flexShrink: 0,
            marginTop: 1,
            width: 14,
            height: 14,
            borderRadius: "50%",
            background: "#d4893a",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 8,
            fontWeight: 900,
            color: "#fff",
            letterSpacing: 0,
          }}>!</span>
          <span>{infoNote}</span>
        </div>
      )}
    </div>
  );
}