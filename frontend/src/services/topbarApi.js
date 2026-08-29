import assetsData from "../data/sample_data/assets.json";
import nftCollectionsData from "../data/sample_data/nftCollections.json";
import notificationsData from "../data/sample_data/notifications.json";
import userData from "../data/sample_data/user.json";
import { USE_MOCK } from "../config";
import { apiFetch } from "./apiClient";
import { getStoredUser } from "../hooks/useAuth";

const SIM_DELAY = 200;
const delay = (fn) => new Promise((resolve) => setTimeout(() => resolve(fn()), SIM_DELAY));

const SEARCH_RESULT_LIMIT = 5;

function matches(haystack, query) {
  return (haystack || "").toLowerCase().includes(query.toLowerCase());
}

function initialsFor(name) {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  return (parts[0][0] + (parts[1]?.[0] || "")).toUpperCase();
}

export const topbarApi = {
  getCurrentUser: async () => {
    if (USE_MOCK) {
      return delay(() => ({
        name: userData.name,
        email: userData.email,
        initials: userData.avatarInitials,
        color: userData.avatarColor,
      }));
    }
    try {
      const profile = await apiFetch("/profile");
      return {
        name: profile.name || "User",
        email: profile.email || "",
        initials: profile.avatar_initials || initialsFor(profile.name),
        color: profile.avatar_color || "var(--sv2-accent)",
      };
    } catch (e) {
      const stored = getStoredUser();
      if (!stored) return { name: "Signed out", email: "", initials: "?", color: "var(--sv2-accent)" };
      return {
        name: stored.name,
        email: stored.email,
        initials: initialsFor(stored.name),
        color: "var(--sv2-accent)",
      };
    }
  },

  getNotifications: async () => {
    if (USE_MOCK) {
      return delay(() => ({
        items: notificationsData.notifications,
        unreadCount: notificationsData.unreadCount,
      }));
    }
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

  markNotificationRead: async (id) => {
    if (USE_MOCK) return delay(() => ({ status: "read" }));
    return apiFetch(`/notifications/${id}/read`, { method: "PATCH" });
  },

  search: async (query) => {
    const q = query.trim();
    if (!q) return { assets: [], collections: [] };

    if (USE_MOCK) {
      return delay(() => {
        const assets = assetsData.assets
          .filter((a) => matches(a.name, q) || matches(a.symbol, q))
          .slice(0, SEARCH_RESULT_LIMIT)
          .map((a) => ({
            id: a.symbol,
            kind: "asset",
            symbol: a.symbol,
            name: a.name,
            subtitle: a.subcategory,
            price: a.price,
            aaiScore: a.aai?.score ?? null,
            held: !!a.held,
            watching: !!a.watching,
          }));

        const collections = nftCollectionsData.collections
          .filter((c) => matches(c.name, q) || matches(c.symbol, q))
          .slice(0, SEARCH_RESULT_LIMIT)
          .map((c) => ({
            id: c.slug,
            kind: "collection",
            symbol: c.symbol,
            name: c.name,
            subtitle: c.subcategory,
            floorUsd: c.floorUsd,
            aaiScore: c.aai?.score ?? null,
            held: !!c.held,
            watching: !!c.watching,
          }));

        return { assets, collections };
      });
    }

    try {
      const res = await apiFetch(`/search?q=${encodeURIComponent(q)}&limit=10`);
      const assets = (res.assets || []).map((a) => ({
        id: a.symbol,
        kind: "asset",
        symbol: a.symbol,
        name: a.name,
        subtitle: a.subcategory || a.category,
        price: a.price,
        aaiScore: a.aai_score,
        held: !!a.held,
        watching: !!a.watching,
      }));

      const collections = (res.nft_collections || []).map((c) => ({
        id: c.slug,
        kind: "collection",
        symbol: c.symbol || c.slug.slice(0, 3).toUpperCase(),
        name: c.name,
        subtitle: "NFT Collection",
        floorUsd: c.floor_usd,
        aaiScore: c.aai_score,
        held: !!c.held,
        watching: !!c.watching,
      }));

      return { assets, collections };
    } catch (e) {
      console.error("Database search failed, falling back to local dataset:", e);
      const assets = assetsData.assets
        .filter((a) => matches(a.name, q) || matches(a.symbol, q))
        .slice(0, SEARCH_RESULT_LIMIT)
        .map((a) => ({
          id: a.symbol,
          kind: "asset",
          symbol: a.symbol,
          name: a.name,
          subtitle: a.subcategory,
          price: a.price,
          aaiScore: a.aai?.score ?? null,
          held: !!a.held,
          watching: !!a.watching,
        }));

      const collections = nftCollectionsData.collections
        .filter((c) => matches(c.name, q) || matches(c.symbol, q))
        .slice(0, SEARCH_RESULT_LIMIT)
        .map((c) => ({
          id: c.slug,
          kind: "collection",
          symbol: c.symbol,
          name: c.name,
          subtitle: c.subcategory,
          floorUsd: c.floorUsd,
          aaiScore: c.aai?.score ?? null,
          held: !!c.held,
          watching: !!c.watching,
        }));

      return { assets, collections };
    }
  },
};