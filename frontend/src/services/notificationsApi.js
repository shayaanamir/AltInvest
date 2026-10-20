import { apiFetch } from "./apiClient";

// Raised after anything changes read state or removes a notification, so the bell's count and the
// Notifications page stay in step. Pass `onNotificationsChanged` as useAsync's `subscribe` option.
const target = new EventTarget();
export function notifyNotificationsChanged() {
  target.dispatchEvent(new Event("changed"));
}
export function onNotificationsChanged(handler) {
  target.addEventListener("changed", handler);
  return () => target.removeEventListener("changed", handler);
}

function mapNotification(n) {
  return {
    id: n.id,
    type: n.type,
    title: n.title,
    message: n.message,
    read: n.read,
    timestamp: n.timestamp,
    deepLink: n.deep_link,
    alertId: n.alert_id || null,
  };
}

const changed = (res) => {
  notifyNotificationsChanged();
  return res;
};

export const notificationsApi = {
  /** A page of notifications, newest first. */
  list: async ({ offset = 0, limit = 20, unreadOnly = false, types = [] } = {}) => {
    const params = new URLSearchParams({ offset, limit, unread_only: unreadOnly });
    types.forEach((t) => params.append("type", t));
    return (await apiFetch(`/notifications?${params}`)).map(mapNotification);
  },

  /** The real unread total (not just among the ones loaded). */
  unreadCount: async () => (await apiFetch("/notifications/unread-count")).count,

  markRead: (id) => apiFetch(`/notifications/${id}/read`, { method: "PATCH" }).then(changed),
  markAllRead: () => apiFetch("/notifications/read-all", { method: "POST" }).then(changed),
  dismiss: (id) => apiFetch(`/notifications/${id}`, { method: "DELETE" }).then(changed),
};

export const NOTIFICATION_TYPE_LABELS = {
  alert_triggered: "Alert",
  market_event: "Market",
  system: "System",
};

/**
 * Where a notification leads. Uses its deep link when it has one, otherwise a sensible page for
 * its type, so every notification goes somewhere.
 */
export function notificationHref(n) {
  const link = n.deepLink || {};
  switch (link.page) {
    case "AssetDetail":
      if (link.symbol) return `/asset-detail?symbol=${encodeURIComponent(link.symbol)}`;
      break;
    case "NFTCollectionDetail":
    case "Discover":
      return "/discover?category=nft";
    case "Portfolio":
      return "/portfolio";
    case "Watchlists":
      return "/watchlists";
    case "Alerts":
      return "/alerts";
    case "Sentiment":
      return "/sentiment";
    case "Dashboard":
      return "/dashboard";
    case "Settings":
      return "/settings";
    case "Profile":
      return "/profile";
    default:
      break;
  }
  if (n.type === "alert_triggered") return "/alerts";
  if (n.type === "market_event") return "/dashboard";
  return "/notifications";
}
