// Money formatters. Every amount in the database is USD; these convert it to the user's display
// currency (Settings > Preferences) with the latest stored exchange rate, and fall back to USD when
// no rate is available.
import { getDisplayCurrency } from "../services/appPreferences";

const _fmtCache = new Map();
function nf(currency, opts = {}) {
  const key = currency + JSON.stringify(opts);
  if (!_fmtCache.has(key)) _fmtCache.set(key, new Intl.NumberFormat(undefined, { style: "currency", currency, ...opts }));
  return _fmtCache.get(key);
}

// The currency's normal number of decimals (2 for USD/EUR/GBP/INR, 0 for JPY).
const currencyDigits = (currency) => nf(currency).resolvedOptions().maximumFractionDigits;

const bad = (v) => v == null || Number.isNaN(v);

function convert(usd) {
  const { code, rate } = getDisplayCurrency();
  return { value: usd * rate, code };
}

export function formatCurrencyFull(usd) {
  const { value, code } = convert(bad(usd) ? 0 : usd);
  const d = currencyDigits(code);
  return nf(code, { minimumFractionDigits: d, maximumFractionDigits: d }).format(value);
}

// Whole units, comma-separated, no cents — for compact summary rows.
export function formatCurrencyWhole(usd) {
  const { value, code } = convert(bad(usd) ? 0 : usd);
  return nf(code, { minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(Math.round(value));
}

// K/M/B/T suffixes on purpose: Intl's compact notation follows the browser locale (en-IN gives "L"/"Cr").
const SCALES = [[1e12, "T"], [1e9, "B"], [1e6, "M"], [1e3, "K"]];

export function formatCurrencyCompact(usd, { digits = 2 } = {}) {
  const { value, code } = convert(bad(usd) ? 0 : usd);
  const scale = SCALES.find(([n]) => Math.abs(value) >= n);
  if (!scale) return nf(code, { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value);
  const parts = nf(code, { minimumFractionDigits: digits, maximumFractionDigits: digits }).formatToParts(value / scale[0]);
  // Put the suffix straight after the number, wherever the locale puts the currency symbol.
  const lastDigit = parts.map((p) => p.type).findLastIndex((t) => t === "integer" || t === "fraction");
  parts.splice(lastDigit + 1, 0, { value: scale[1] });
  return parts.map((p) => p.value).join("");
}

// Adaptive precision so 71,450 doesn't show 2 decimals while 0.187 doesn't show 0.
export function formatAssetPrice(usd) {
  const { value, code } = convert(bad(usd) ? 0 : usd);
  const abs = Math.abs(value);
  const d = abs >= 1000 ? 0 : abs >= 1 ? 2 : 4;
  return nf(code, { minimumFractionDigits: d, maximumFractionDigits: d }).format(value);
}

// Short chart-axis label: 1.2K / 64.3K above a thousand, adaptive below.
export function formatCurrencyAxis(usd) {
  const { value } = convert(bad(usd) ? 0 : usd);
  return Math.abs(value) >= 1000 ? formatCurrencyCompact(usd, { digits: 1 }) : formatAssetPrice(usd);
}

/**
 * Always USD, never converted — for amounts the user enters or that are stored as USD on purpose
 * (alert price thresholds, average buy price). Shows the "USD" code when the display currency is
 * something else, so it can't be mistaken for a converted figure.
 */
export function formatUsd(usd) {
  const showCode = getDisplayCurrency().code !== "USD";
  const v = bad(usd) ? 0 : usd;
  const d = Math.abs(v) >= 1000 ? 0 : Math.abs(v) >= 1 ? 2 : 4;
  return nf("USD", { currencyDisplay: showCode ? "code" : "symbol", minimumFractionDigits: d, maximumFractionDigits: d }).format(v);
}

export function formatPct(value, { withSign = false } = {}) {
  if (value == null || Number.isNaN(value)) return "0.00%";
  const sign = withSign && value > 0 ? "+" : "";
  return sign + value.toFixed(2) + "%";
}
