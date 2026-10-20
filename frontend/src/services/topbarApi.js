import { apiFetch } from "./apiClient";
import { fetchUniverse } from "./assetRepository";
import { getStoredUser } from "../hooks/useAuth";
import { authApi } from "./authApi";

const SEARCH_RESULT_LIMIT = 5;

function initialsFor(name) {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  return (parts[0][0] + (parts[1]?.[0] || "")).toUpperCase();
}

export const topbarApi = {
  getCurrentUser: async () => {
    try {
      const user = await authApi.me();
      return {
        name: user.name || "User",
        email: user.email || "",
        initials: user.avatar_initials || initialsFor(user.name),
        color: user.avatar_color || "var(--sv2-accent)",
      };
    } catch (e) {
      const stored = getStoredUser();
      if (!stored) throw e; // nothing to show, let the menu offer a retry
      return {
        name: stored.name,
        email: stored.email,
        initials: initialsFor(stored.name),
        color: "var(--sv2-accent)",
        stale: true, // from the saved login, not freshly loaded
      };
    }
  },

  getNotifications: async () => {
    const items = await apiFetch("/notifications?limit=20");
    const mapped = items.map((n) => ({
      id: n.id,
      type: n.type,
      title: n.title,
      message: n.message,
      read: n.read,
      timestamp: n.timestamp,
      deepLink: n.deep_link,
    }));
    return { items: mapped, unreadCount: mapped.filter((n) => !n.read).length };
  },

  markNotificationRead: async (id) => apiFetch(`/notifications/${id}/read`, { method: "PATCH" }),

  // Search runs against the same covered-universe rows Discover uses, so each result carries
  // its stored price / floor, AAI score and the user's held / watching flags.
  search: async (query) => {
    const q = query.trim();
    if (!q) return { assets: [], collections: [] };

    const rows = await fetchUniverse({ category: "all", q, sort: "market_cap", order: "desc" });

    const assets = rows
      .filter((r) => r.type === "crypto")
      .slice(0, SEARCH_RESULT_LIMIT)
      .map((a) => ({
        id: a.symbol,
        kind: "asset",
        symbol: a.symbol,
        name: a.name,
        subtitle: a.subcategory,
        price: a.price,
        aaiScore: a.aaiScore,
        held: a.held,
        watching: a.watching,
      }));

    const collections = rows
      .filter((r) => r.type === "nft")
      .slice(0, SEARCH_RESULT_LIMIT)
      .map((c) => ({
        id: c.id,
        kind: "collection",
        symbol: c.symbol,
        name: c.name,
        subtitle: c.subcategory || "NFT Collection",
        floorUsd: c.price,
        aaiScore: c.aaiScore,
        held: c.held,
        watching: c.watching,
      }));

    return { assets, collections };
  },
};
