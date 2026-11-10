// Illustrative 30-day volatility cone for the asset price chart (ml/docs/DECISIONS.md D52).
//
// Built only from the `volatility` the ML service already serves on /risk: annualised EWMA vol (D51).
// It is NOT a tested price range: no price or range model is approved, so lower_bound / upper_bound stay null
// and no predicted price line is drawn. Pure functions, no React, so they can be unit-tested with `node --test`.

// The annualisation factor serving uses: volatility = daily EWMA vol x sqrt(ANNUALISATION_DAYS)
// (ml/config.py ANNUALISATION_DAYS, ml/serving/responses.py). A test checks the two stay equal.
export const ANNUALISATION_DAYS = 365;
export const CONE_DAYS = 30;
export const Z_INNER = 0.6745; // inner 50% band (normal 25th / 75th percentile)
export const Z_OUTER = 1.2816; // outer 80% band (normal 10th / 90th percentile)
export const CONE_CAPTION = "Likely price range based on recent volatility, not a price prediction.";

// The future section gets its true share of the time axis, but never less than this share of the plot width,
// so the 30-day cone stays readable next to a long history (1Y: 30 / 395 days would be about 7.6%).
export const MIN_FUTURE_SHARE = 0.15;

const DAY_MS = 86400000;
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** Share of the plot width for the cone's days after `histSpanDays` of history. */
export function futureShare(histSpanDays, coneDays = CONE_DAYS) {
  return Math.max(coneDays / (Math.max(1, histSpanDays) + coneDays), MIN_FUTURE_SHARE);
}

/** 'YYYY-MM-DD' -> '8 Nov' (UTC, as the daily closes are). */
export function shortDate(isoDate) {
  const d = new Date(`${isoDate}T00:00:00Z`);
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`;
}

/**
 * Label for the cone's start point. The cone starts at the last daily close, not at the page header price
 * (that comes from asset_market_data, which is demo seed data, not a market price), so the chart says which.
 */
export function coneStartLabel(isoDate) {
  return `Last close, ${shortDate(isoDate)}`;
}

/** Daily vol from the served annualised vol. */
export function dailyVol(annualVol, n = ANNUALISATION_DAYS) {
  return annualVol / Math.sqrt(n);
}

/** Price band d days ahead: lastClose x exp(-/+ z x sd x sqrt(d)). Width is 0 at d = 0. */
export function coneBand(lastClose, sd, d, z) {
  const k = z * sd * Math.sqrt(d);
  return { lower: lastClose * Math.exp(-k), upper: lastClose * Math.exp(k) };
}

/**
 * The served annualised vol when the cone may be drawn, else null. Hidden when the value is missing, null or
 * not a positive number, when the risk note is not the ML's served EWMA model (for example mock data for an
 * asset ML does not cover), or when the risk data is stale.
 */
export function coneVolatility(risk) {
  if (!risk) return null;
  const v = risk.volatility;
  if (typeof v !== "number" || !Number.isFinite(v) || v <= 0) return null;
  const note = typeof risk.note === "string" ? risk.note : "";
  if (!note.includes("EWMA volatility")) return null;
  if (note.toLowerCase().includes("data stale")) return null;
  return v;
}

function addDays(isoDate, d) {
  return new Date(new Date(`${isoDate}T00:00:00Z`).getTime() + d * DAY_MS).toISOString().slice(0, 10);
}

/**
 * Cone points for d = 0..days from the last history point ({date: 'YYYY-MM-DD', price}).
 * Returns null when the cone must be hidden (see coneVolatility) or there is no last close.
 */
export function buildCone(lastPoint, risk, days = CONE_DAYS) {
  const annual = coneVolatility(risk);
  if (annual == null || !lastPoint || !(lastPoint.price > 0)) return null;
  const sd = dailyVol(annual);
  return Array.from({ length: days + 1 }, (_, d) => ({
    d,
    date: addDays(lastPoint.date, d),
    inner: coneBand(lastPoint.price, sd, d, Z_INNER),
    outer: coneBand(lastPoint.price, sd, d, Z_OUTER),
  }));
}

/**
 * The layers the price chart draws, in order. There is never a forecast or center line (D52):
 * "history" always (with at least 2 points), plus "cone-outer" and "cone-inner" when a cone can be built.
 */
export function chartLayers(history, risk) {
  if (!history || history.length < 2) return { layers: [], cone: null };
  const cone = buildCone(history[history.length - 1], risk);
  return { layers: cone ? ["history", "cone-outer", "cone-inner"] : ["history"], cone };
}
