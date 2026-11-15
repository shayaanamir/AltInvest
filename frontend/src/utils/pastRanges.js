// Past ranges on the asset price chart (Phase 11, ml/docs/DECISIONS.md D87-D89).
//
// For each past day, the 50% / 80% range the volatility cone (utils/volCone.js, D52) would have shown 30 days
// earlier. The ML service computes them strictly as of that earlier day (the same cone formula, the volatility
// served then); the backend sends them only when the chart's prices are the closes they were built from (D89).
// Descriptive only: no direction, no drift, not a price prediction. Pure functions, tested with `node --test`.

export const PAST_RANGES_CAPTION = "Shaded history: the range shown 30 days earlier for each day. Not a price prediction.";
export const PAST_RANGES_TOGGLE_LABEL = "Show past ranges";
// D88: fewer days than this in the visible window and no calibration line is shown (ml/config.py
// PAST_RANGE_MIN_CALIBRATION_DAYS; a test checks the two stay equal).
export const MIN_CALIBRATION_DAYS = 60;

const num = (v) => typeof v === "number" && Number.isFinite(v);

/**
 * The past-range points for the dates of the visible history, oldest first:
 * [{date, inner: {lower, upper}, outer: {lower, upper}, close}]. Points with a missing or invalid number, or a
 * date outside the visible history, are left out. Empty when there are no past ranges.
 */
export function pastBandsForWindow(pastRanges, history) {
  if (!pastRanges || !Array.isArray(pastRanges.points) || !history || history.length === 0) return [];
  const dates = new Set(history.map((h) => h.date));
  return pastRanges.points
    .filter((p) => dates.has(p.date)
      && [p.inner_lower, p.inner_upper, p.outer_lower, p.outer_upper, p.close].every(num)
      && p.outer_lower <= p.inner_lower && p.inner_lower <= p.inner_upper && p.inner_upper <= p.outer_upper)
    .map((p) => ({
      date: p.date,
      inner: { lower: p.inner_lower, upper: p.inner_upper },
      outer: { lower: p.outer_lower, upper: p.outer_upper },
      close: p.close,
    }))
    .sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));
}

/**
 * Share of the visible days whose close was inside each past band (bounds inclusive), or null when fewer than
 * MIN_CALIBRATION_DAYS days have a band (D88). Uses only the as-of bands and the close of each day, the same
 * numbers the ML coverage report counts (ml/serving/past_ranges.py coverage).
 */
export function calibration(bands) {
  if (!bands || bands.length < MIN_CALIBRATION_DAYS) return null;
  const inside = (b, key) => b[key].lower <= b.close && b.close <= b[key].upper;
  const in50 = bands.filter((b) => inside(b, "inner")).length;
  const in80 = bands.filter((b) => inside(b, "outer")).length;
  return { days: bands.length, share50: in50 / bands.length, share80: in80 / bands.length };
}

const pct = (x) => `${Math.round(x * 100)}%`;

/** "Over these 91 days, the price stayed inside the 80% range on 77% of days and inside the 50% range on 49%." */
export function calibrationText(c) {
  if (!c) return null;
  return `Over these ${c.days} days, the price stayed inside the 80% range on ${pct(c.share80)} of days `
    + `and inside the 50% range on ${pct(c.share50)}.`;
}
