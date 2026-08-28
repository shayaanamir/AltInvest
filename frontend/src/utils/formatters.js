export function formatCurrencyFull(value) {
  if (value == null || Number.isNaN(value)) return "$0.00";
  return "$" + value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function formatCurrencyCompact(value) {
  if (value == null || Number.isNaN(value)) return "$0";
  const abs = Math.abs(value);
  if (abs >= 1e12) return "$" + (value / 1e12).toFixed(2) + "T";
  if (abs >= 1e9) return "$" + (value / 1e9).toFixed(2) + "B";
  if (abs >= 1e6) return "$" + (value / 1e6).toFixed(2) + "M";
  if (abs >= 1e3) return "$" + (value / 1e3).toFixed(2) + "K";
  return "$" + value.toFixed(2);
}

// Adaptive precision so $71,450 doesn't show 2 decimals while $0.187 doesn't show 0.
export function formatAssetPrice(value) {
  if (value == null || Number.isNaN(value)) return "$0.00";
  if (value >= 1000) return "$" + value.toLocaleString(undefined, { maximumFractionDigits: 0 });
  if (value >= 1) return "$" + value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return "$" + value.toFixed(4);
}

export function formatPct(value, { withSign = false } = {}) {
  if (value == null || Number.isNaN(value)) return "0.00%";
  const sign = withSign && value > 0 ? "+" : "";
  return sign + value.toFixed(2) + "%";
}