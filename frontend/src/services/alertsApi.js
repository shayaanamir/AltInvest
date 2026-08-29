import { USE_MOCK } from "../config";
import { apiFetch } from "./apiClient";
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

function mapBackendAlert(a) {
  const shaped = {
    id: a.id,
    targetType: a.target_type,
    targetSymbol: a.target_symbol,
    targetSlug: a.target_slug,
    targetName: a.target_name,
    metricType: a.metric_type,
    condition: a.condition,
    thresholdValue: a.threshold_value,
    status: a.status,
    deliveryChannel: a.delivery_channel,
    createdAt: a.created_at,
    lastTriggeredAt: a.last_triggered_at,
    lastObservedValue: a.last_observed_value,
  };
  return normaliseAlert(shaped);
}

export const alertsApi = {
  getAlerts: async () => {
    if (USE_MOCK) return delay(() => alertsData.alerts.map(normaliseAlert));
    const alerts = await apiFetch("/alerts");
    return alerts.map(mapBackendAlert);
  },

  getMetricOptions: async () => {
    if (USE_MOCK) return delay(() => alertsData.metricTypeOptions);
    // Not backend-driven — these are fixed enum options mirrored from
    // backend/routes/alerts.py's _VALID_METRIC_TYPES.
    return delay(() => alertsData.metricTypeOptions);
  },

  getConditionOptions: async () => {
    if (USE_MOCK) return delay(() => alertsData.conditionOptions);
    return delay(() => alertsData.conditionOptions);
  },

  // ── mutations ──────────────────────────────────────────────────────────

  createAlert: async (payload) => {
    // payload matches backend/models/schemas.py::AlertCreate, e.g.:
    // { target_type: "crypto", target_symbol: "BTC", target_name: "Bitcoin",
    //   metric_type: "price", condition: "above", threshold_value: 80000,
    //   delivery_channel: "push" }
    if (USE_MOCK) return delay(() => ({ id: `alt_${Date.now()}` }));
    return apiFetch("/alerts", { method: "POST", body: JSON.stringify(payload) });
  },

  toggleAlert: async (id, nextStatus) => {
    // nextStatus is "active" or "paused"
    if (USE_MOCK) return delay(() => ({ status: "updated" }));
    return apiFetch(`/alerts/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status: nextStatus }),
    });
  },

  deleteAlert: async (id) => {
    if (USE_MOCK) return delay(() => null);
    return apiFetch(`/alerts/${id}`, { method: "DELETE" });
  },
};