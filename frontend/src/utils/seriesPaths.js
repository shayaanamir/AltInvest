// The SVG paths of a line/area chart from a series of values or { value } points. Pure, so it can be unit-tested.
export function buildSeriesPaths(data, width, height, { padLeft = 0, padRight = 0, padTop = 0, padBottom = 0 } = {}) {
  if (!data || data.length < 2) return null;
  const vals = data.map((d) => (typeof d === "number" ? d : d.value));
  const minV = Math.min(...vals) * 0.98;
  const maxV = Math.max(...vals) * 1.02;
  const range = Math.max(1, maxV - minV);

  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  const pts = data.map((d, i) => {
    const v = typeof d === "number" ? d : d.value;
    return {
      x: padLeft + (i / (data.length - 1)) * plotW,
      y: height - padBottom - ((v - minV) / range) * plotH,
    };
  });
  const last = pts[pts.length - 1];
  const linePath = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
  const areaPath = `${linePath} L ${last.x.toFixed(1)} ${height - padBottom} L ${pts[0].x.toFixed(1)} ${height - padBottom} Z`;

  return { pts, last, linePath, areaPath, minV, maxV, range };
}
