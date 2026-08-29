import assetsData from "../data/sample_data/assets.json";
import nftCollectionsData from "../data/sample_data/nftCollections.json";
import notificationsData from "../data/sample_data/notifications.json";
import userData from "../data/sample_data/user.json";

const SIM_DELAY = 200;
const delay = (fn) => new Promise((resolve) => setTimeout(() => resolve(fn()), SIM_DELAY));

const SEARCH_RESULT_LIMIT = 5;

function matches(haystack, query) {
  return (haystack || "").toLowerCase().includes(query.toLowerCase());
}

export const topbarApi = {
  getCurrentUser: () =>
    delay(() => ({
      name: userData.name,
      email: userData.email,
      initials: userData.avatarInitials,
      color: userData.avatarColor,
    })),

  getNotifications: () =>
    delay(() => ({
      items: notificationsData.notifications,
      unreadCount: notificationsData.unreadCount,
    })),

  search: (query) =>
    delay(() => {
      const q = query.trim();
      if (!q) return { assets: [], collections: [] };

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
    }),
};