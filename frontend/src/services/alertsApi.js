import { apiFetch } from "./apiClient";
import { fetchUniverse } from "./assetRepository";
import { ALERT_METRIC_OPTIONS, ALERT_CONDITION_OPTIONS } from "../content/uiOptions";

const METRIC_LABELS = {
  price: "Price",
  aai_score: "AAI score",
  sentiment: "Sentiment",
  risk: "Risk score",
};

// Avatar colour/symbol come from the same covered-universe rows Discover uses.
function lookupAvatar(alert, universe) {
  if (alert.targetType === "nft" && alert.targetSlug) {
    const c = universe.find((x) => x.type === "nft" && x.id === alert.targetSlug);
    return {
      color: c?.color || "#8892a6",
      symbol: c?.symbol || alert.targetSlug.slice(0, 3).toUpperCase(),
    };
  }
  const a = universe.find((x) => x.type === "crypto" && x.symbol === alert.targetSymbol);
  return {
    color: a?.color || "#8892a6",
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

function normaliseAlert(a, universe) {
  const avatar = lookupAvatar(a, universe);
  return {
    ...a,
    name: a.targetName,
    avatarColor: avatar.color,
    avatarSymbol: avatar.symbol,
    conditionText: describeCondition(a),
  };
}

function mapBackendAlert(a, universe) {
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
  return normaliseAlert(shaped, universe);
}

export const alertsApi = {
  getAlerts: async () => {
    const [alerts, universe] = await Promise.all([
      apiFetch("/alerts"),
      fetchUniverse({ category: "all" }).catch(() => []), // avatars degrade to grey; the alerts themselves still load
    ]);
    return alerts.map((a) => mapBackendAlert(a, universe));
  },

  // Fixed enum options mirrored from backend/routes/alerts.py.
  getMetricOptions: async () => ALERT_METRIC_OPTIONS,
  getConditionOptions: async () => ALERT_CONDITION_OPTIONS,

  // ── mutations ──────────────────────────────────────────────────────────

  createAlert: async (payload) => {
    // payload matches backend/models/schemas.py::AlertCreate, e.g.:
    // { target_type: "crypto", target_symbol: "BTC", target_name: "Bitcoin",
    //   metric_type: "price", condition: "above", threshold_value: 80000,
    //   delivery_channel: "push" }
    return apiFetch("/alerts", { method: "POST", body: JSON.stringify(payload) });
  },

  toggleAlert: async (id, nextStatus) => {
    // nextStatus is "active" or "paused"
    return apiFetch(`/alerts/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status: nextStatus }),
    });
  },

  deleteAlert: async (id) => apiFetch(`/alerts/${id}`, { method: "DELETE" }),
};
