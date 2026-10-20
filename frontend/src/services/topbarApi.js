import { apiFetch } from "./apiClient";
import { fetchUniverse } from "./assetRepository";
import { getStoredUser } from "../hooks/useAuth";

const SEARCH_RESULT_LIMIT = 5;

function initialsFor(name) {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  return (parts[0][0] + (parts[1]?.[0] || "")).toUpperCase();
}

export const topbarApi = {
  getCurrentUser: async () => {
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

  // The signed-in user's recent searches (server-side, de-duplicated, newest first).
  getRecentSearches: async () => (await apiFetch("/search/history?limit=6")).map((h) => h.query),
  recordSearch: (query) => apiFetch("/search/history", { method: "POST", body: JSON.stringify({ query }) }),
  clearRecentSearches: () => apiFetch("/search/history", { method: "DELETE" }),

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
