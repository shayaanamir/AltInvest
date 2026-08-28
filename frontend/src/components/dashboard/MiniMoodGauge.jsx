function polarToCartesian(cx, cy, r, angleDeg) {
  const rad = (angleDeg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy - r * Math.sin(rad) };
}

function describeArc(cx, cy, r, startAngle, endAngle) {
  const start = polarToCartesian(cx, cy, r, startAngle);
  const end = polarToCartesian(cx, cy, r, endAngle);
  const large = Math.abs(startAngle - endAngle) <= 180 ? "0" : "1";
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${large} 1 ${end.x} ${end.y}`;
}

const CX = 34;
const CY = 34;
const R = 24;
const SW = 7;
const SEG = [
  [179, 102],
  [99, 81],
  [78, 1],
];

export default function MiniMoodGauge({ score = 50 }) {
  const pct = Math.max(0, Math.min(100, score));
  const needleAngle = 180 - (pct / 100) * 180;
  const tip = polarToCartesian(CX, CY, R - 8, needleAngle);

  return (
    <svg width="64" height="38" viewBox="4 8 60 30" className="dv2-mood-gauge">
      <path d={describeArc(CX, CY, R, ...SEG[0])} stroke="var(--sv2-red)" strokeWidth={SW} fill="none" strokeLinecap="butt" />
      <path d={describeArc(CX, CY, R, ...SEG[1])} stroke="var(--sv2-grey-arc)" strokeWidth={SW} fill="none" strokeLinecap="butt" />
      <path d={describeArc(CX, CY, R, ...SEG[2])} stroke="var(--sv2-green)" strokeWidth={SW} fill="none" strokeLinecap="butt" />
      <line x1={CX} y1={CY} x2={tip.x} y2={tip.y} stroke="#9ea5be" strokeWidth="2" strokeLinecap="round" />
      <circle cx={CX} cy={CY} r="3" fill="#9ea5be" />
    </svg>
  );
}