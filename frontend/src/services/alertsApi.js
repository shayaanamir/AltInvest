import alertsData from "../data/sample_data/alerts.json";
import assetsData from "../data/sample_data/assets.json";
import nftData from "../data/sample_data/nftCollections.json";

const SIM_DELAY = 300;
function delay(fn) {
  return new Promise((resolve) => setTimeout(() => resolve(fn()), SIM_DELAY));
}

const METRIC_LABELS = {
  price: "Price",
  aai_score: "AAI score",
  sentiment: "Sentiment",
  risk: "Risk score",
};

function lookupAvatar(alert) {
  if (alert.targetType === "nft" && alert.targetSlug) {
    const c = nftData.collections.find((x) => x.slug === alert.targetSlug);
    return {
      color: c?.bannerColor || "#8892a6",
      symbol: c?.symbol || alert.targetSlug.slice(0, 3).toUpperCase(),
    };
  }
  const a = assetsData.assets.find((x) => x.symbol === alert.targetSymbol);
  return {
    color: a?.logoColor || "#8892a6",
    symbol: a?.symbol || (alert.targetSymbol || "").slice(0, 3).toUpperCase(),
  };
}

function formatThreshold(metricType, value) {
  if (value == null) return "";
  if (metricType === "price") return `$${value.toLocaleString()}`;
  return `${value}`;
}

export function describeCondition(alert) {
  const metricLabel = METRIC_LABELS[alert.metricType] || alert.metricType;
  const threshold = formatThreshold(alert.metricType, alert.thresholdValue);
  switch (alert.condition) {
    case "above":
      return `${metricLabel} rises above ${threshold}`;
    case "below":
      return `${metricLabel} drops below ${threshold}`;
    case "shifts_bearish":
      return `${metricLabel} shifts bearish`;
    case "shifts_bullish":
      return `${metricLabel} shifts bullish`;
    default:
      return metricLabel;
  }
}

function normaliseAlert(a) {
  const avatar = lookupAvatar(a);
  return {
    ...a,
    name: a.targetName,
    avatarColor: avatar.color,
    avatarSymbol: avatar.symbol,
    conditionText: describeCondition(a),
  };
}

export const alertsApi = {
  getAlerts: async () => delay(() => alertsData.alerts.map(normaliseAlert)),
  getMetricOptions: async () => delay(() => alertsData.metricTypeOptions),
  getConditionOptions: async () => delay(() => alertsData.conditionOptions),
};