// Small generative "arcs" motif used as cover art for NFT holdings, since
// there's no real image asset in the sample data — tinted by the
// holding's own `artColor` field so it still reads as data-driven.
export default function NftArtPlaceholder({ color = "#c9805a", seed = 1 }) {
  const rings = [0.92, 0.74, 0.58, 0.44, 0.32, 0.22, 0.14];
  const cx = 100, cy = 100;

  return (
    <svg viewBox="0 0 200 200" width="100%" height="100%" preserveAspectRatio="xMidYMid slice">
      <rect width="200" height="200" fill={`${color}14`} />
      {rings.map((r, i) => {
        const radius = r * 90;
        const start = (seed * 37 + i * 53) % 360;
        const sweep = 140 + ((seed + i) % 4) * 30;
        const end = start + sweep;
        const startRad = (start * Math.PI) / 180;
        const endRad = (end * Math.PI) / 180;
        const x1 = cx + radius * Math.cos(startRad);
        const y1 = cy + radius * Math.sin(startRad);
        const x2 = cx + radius * Math.cos(endRad);
        const y2 = cy + radius * Math.sin(endRad);
        const large = sweep > 180 ? 1 : 0;

        return (
          <path
            key={i}
            d={`M ${x1.toFixed(1)} ${y1.toFixed(1)} A ${radius.toFixed(1)} ${radius.toFixed(1)} 0 ${large} 1 ${x2.toFixed(1)} ${y2.toFixed(1)}`}
            fill="none"
            stroke={color}
            strokeWidth={3.5}
            strokeLinecap="round"
            opacity={0.9 - i * 0.09}
          />
        );
      })}
    </svg>
  );
}