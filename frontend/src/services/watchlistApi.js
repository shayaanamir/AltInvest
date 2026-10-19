import { apiFetch } from "./apiClient";
import { fetchUniverse } from "./assetRepository";

// ── real-data mapping ────────────────────────────────────────────────────
// /watchlists returns each item with its stored price / 24h change / AAI. Colour, symbol,
// subcategory and the BUY/HOLD/SELL signal come from the covered-universe row for the same
// asset (GET /discover), so everything shown is a database value.

function mapBackendItem(item, universeById) {
  const isNft = item.type === "nft";
  const match = universeById.get(item.symbol_or_slug);
  return {
    id: item.symbol_or_slug,
    type: item.type,
    symbol: match?.symbol || (isNft ? item.symbol_or_slug.slice(0, 5).toUpperCase() : item.symbol_or_slug),
    name: item.name || match?.name || item.symbol_or_slug,
    subcategory: match?.subcategory || (isNft ? "NFT" : "Crypto"),
    color: match?.color || "var(--sv2-accent)",
    price: item.price ?? match?.price ?? null,
    changePct: item.change_24h ?? match?.changePct ?? 0,
    aaiScore: item.aai_score ?? match?.aaiScore ?? null,
    signal: match?.signal ?? null,
  };
}

function mapBackendList(w, universeById) {
  return {
    id: w.id,
    name: w.name,
    createdAt: w.created_at,
    items: (w.items || []).map((i) => mapBackendItem(i, universeById)),
  };
}

export const watchlistApi = {
  // Shown when the account has no watchlists yet.
  getEmptyState: () => ({
    title: "You have no watchlists yet",
    subtitle: "Track assets you're considering without adding them to your portfolio.",
    cta: "Create Watchlist",
  }),

  getInitialListsAsync: async () => {
    const [lists, universe] = await Promise.all([
      apiFetch("/watchlists"),
      fetchUniverse({ category: "all" }).catch(() => []), // enrichment only; the lists still load without it
    ]);
    const universeById = new Map(universe.map((u) => [u.id, u]));
    return lists.map((l) => mapBackendList(l, universeById));
  },

  // Everything a new watchlist can start with: the whole covered universe.
  getSearchableItems: () => fetchUniverse({ category: "all", sort: "name", order: "asc" }),

  // ── mutations ──────────────────────────────────────────────────────────

  createList: (name) => apiFetch("/watchlists", { method: "POST", body: JSON.stringify({ name }) }),

  deleteList: (watchlistId) => apiFetch(`/watchlists/${watchlistId}`, { method: "DELETE" }),

  addItem: (watchlistId, type, symbolOrSlug) =>
    apiFetch(`/watchlists/${watchlistId}/items`, {
      method: "POST",
      body: JSON.stringify({ type, symbol_or_slug: symbolOrSlug }),
    }),

  removeItem: (watchlistId, symbolOrSlug) =>
    apiFetch(`/watchlists/${watchlistId}/items/${symbolOrSlug}`, { method: "DELETE" }),
};
