// frontend/src/utils/scoring.js

// ---- AAI signal (0-100 score -> label/tone) ----
// Single source of truth. Previously drifted across assetDetailApi.js (75/55/45/25),
// ScoreShowcase.jsx (duplicate of same), and watchlistApi.js (65/45, 3 tiers only).
const AAI_BANDS = [
  { min: 75, label: "Strong Buy", tone: "positive" },
  { min: 55, label: "Buy", tone: "positive" },
  { min: 45, label: "Hold", tone: "neutral" },
  { min: 25, label: "Sell", tone: "negative" },
  { min: -Infinity, label: "Strong Sell", tone: "negative" },
];

export function getAaiSignal(score) {
  if (score == null) return { label: "Hold", tone: "neutral" };
  const band = AAI_BANDS.find((b) => score >= b.min);
  return { label: band.label, tone: band.tone };
}

// Coarser tier used for dot/badge coloring across cards
// (previously: aaiTier in TrendingAssetsSection/TrendingCollectionsSection at 65/45,
// aaiDotColor in DiscoverAssetCard/WatchlistRow at 65/45, aaiColor in
// CryptoHoldingsTable at 70/45, barColor in AssetSentimentList at 58/45 — now one scale).
export function getAaiTier(score) {
  if (score == null) return "unknown";
  if (score >= 65) return "high";
  if (score >= 45) return "medium";
  return "low";
}

export function getAaiTierColor(score) {
  const tier = getAaiTier(score);
  if (tier === "high") return "var(--sv2-green)";
  if (tier === "medium") return "var(--sv2-accent)";
  if (tier === "low") return "var(--sv2-red)";
  return "var(--sv2-text-mute)";
}

// CSS class suffix form, for components using aaiTier() === "" | "medium" | "low" pattern
export function getAaiTierClass(score) {
  const tier = getAaiTier(score);
  return tier === "high" ? "" : tier; // "" | "medium" | "low"
}

// ---- Risk tone ----
// Previously: assetDetailApi.riskLevelTone(level) (string-level based) and
// ScoreShowcase's local riskTone(value, higherIsBetter) (numeric-value based) —
// incompatible signatures, same intent. This supports both call shapes.
export function getRiskTone(input, { higherIsBetter = false } = {}) {
  // String-level form: "low" | "medium" | "high" | "excellent" | "good" | "fair"
  if (typeof input === "string") {
    if (["low", "excellent", "good"].includes(input)) return "positive";
    if (input === "high") return "negative";
    return "neutral"; // medium, fair
  }
  // Numeric form (0-100)
  const value = input;
  if (higherIsBetter) {
    if (value >= 80) return "positive";
    if (value >= 40) return "neutral";
    return "negative";
  }
  if (value >= 60) return "negative";
  if (value >= 30) return "neutral";
  return "positive";
}

// ---- Confidence label wording ----
// Previously: sentimentApi.evidencePhrase() and assetDetailApi.confidenceLabel()
// agreed on "well corroborated / fairly supported / thin evidence", but
// compareApi.evidenceLabel() said "moderately corroborated" for the medium tier —
// a real user-facing text inconsistency. This is now the only implementation.
export function getEvidencePhrase(confidenceLabelOrPct) {
  // Accepts either a label ("high"|"medium"|"low") or a 0-100 pct
  let label = confidenceLabelOrPct;
  if (typeof confidenceLabelOrPct === "number") {
    label = confidenceLabelOrPct >= 70 ? "high" : confidenceLabelOrPct >= 40 ? "medium" : "low";
  }
  if (label === "high") return "well corroborated";
  if (label === "medium") return "fairly supported";
  return "thin evidence";
}

export function confidenceLabelFromValue(v) {
  // v is a 0-1 confidence fraction
  if (v >= 0.7) return "high";
  if (v >= 0.4) return "medium";
  return "low";
}