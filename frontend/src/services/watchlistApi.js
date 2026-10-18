import { USE_MOCK } from "../config";
import { apiFetch } from "./apiClient";
import watchlistsData from "../data/sample_data/watchlists.json";
import assetsData from "../data/sample_data/assets.json";
import nftData from "../data/sample_data/nftCollections.json";
import assetDetailData from "../data/sample_data/assetDetail.json";
import nftDetailData from "../data/sample_data/nftDetail.json";
import { getAaiSignal } from "../utils/scoring";

// Watchlists still enrich their rows from the bundled sample catalogue (out of scope for the
// backend-only Dashboard/Discover/Compare/Asset Detail change). Moved here from assetRepository.js
// unchanged so the Watchlists page behaves exactly as before.
const CRYPTO_ITEMS = assetsData.assets.map((a) => ({
  id: a.symbol,
  type: "crypto",
  symbol: a.symbol,
  name: a.name,
  subcategory: a.subcategory,
  color: a.logoColor,
  price: a.price,
  changePct: a.change24h,
  aaiScore: a.aai.score,
  signal: a.aai.signal,
  sentimentScore: a.sentiment.score,
  volatility: a.risk.volatilityIndex,
  marketCap: a.marketCap,
  held: a.held,
  watching: a.watching,
  sparkline: (assetDetailData[a.symbol]?.priceHistory || []).map((p) => p.price),
}));

const NFT_ITEMS = nftData.collections.map((c) => ({
  id: c.slug,
  type: "nft",
  symbol: c.symbol,
  name: c.name,
  subcategory: c.subcategory,
  color: c.bannerColor,
  price: c.floorUsd,
  changePct: c.change24h,
  aaiScore: c.aai?.score,
  signal: c.aai?.signal,
  sentimentScore: c.sentiment?.score,
  volatility: c.liquidity?.illiquidityRiskScore ?? c.risk?.illiquidityRiskScore ?? c.risk?.volatilityIndex ?? 50,
  marketCap: c.marketCapUsd ?? (c.floorUsd && c.supply ? c.floorUsd * c.supply : 0),
  held: c.held,
  watching: c.watching,
  sparkline: (nftDetailData[c.slug]?.floorHistory || []).map((p) => p.floorEth ?? p.floorUsd ?? p.price ?? 0),
}));

const ALL_ITEMS = [...CRYPTO_ITEMS, ...NFT_ITEMS];

function findMatch(raw) {
  if (raw.type === "crypto") return ALL_ITEMS.find((a) => a.type === "crypto" && a.symbol === raw.symbol);
  return ALL_ITEMS.find((a) => a.type === "nft" && a.id === raw.slug);
}

function deriveSignal(score) {
  if (score == null) return null;
  const label = getAaiSignal(score).label.toUpperCase();
  return label.includes("SELL") ? "SELL" : label.includes("BUY") ? "BUY" : "HOLD";
}

function enrichRawItem(raw) {
  const match = findMatch(raw);
  const isNft = raw.type === "nft";
  return {
    id: isNft ? raw.slug : raw.symbol,
    type: raw.type,
    symbol: match?.symbol || raw.symbol || raw.slug,
    name: raw.name,
    subcategory: match?.subcategory || (isNft ? "NFT" : "Crypto"),
    color: match?.color || "var(--sv2-accent)",
    price: isNft ? (match?.price ?? null) : raw.price,
    changePct: raw.change24h ?? match?.changePct ?? 0,
    aaiScore: raw.aai ?? match?.aaiScore ?? null,
    signal: match?.signal || deriveSignal(raw.aai),
  };
}

function rawFromDiscoverItem(discoverItem) {
  return discoverItem.type === "nft"
    ? {
        type: "nft",
        slug: discoverItem.id,
        name: discoverItem.name,
        change24h: discoverItem.changePct,
        aai: discoverItem.aaiScore,
      }
    : {
        type: "crypto",
        symbol: discoverItem.symbol,
        name: discoverItem.name,
        price: discoverItem.price,
        change24h: discoverItem.changePct,
        aai: discoverItem.aaiScore,
      };
}

// ── real-data mapping ────────────────────────────────────────────────────

function mapBackendItem(item) {
  const isNft = item.type === "nft";
  return {
    id: item.symbol_or_slug,
    type: item.type,
    symbol: item.name && isNft ? undefined : item.symbol_or_slug, // enriched name below covers display
    name: item.name || item.symbol_or_slug,
    subcategory: isNft ? "NFT" : "Crypto",
    color: "var(--sv2-accent)",
    price: item.price,
    changePct: item.change_24h ?? 0,
    aaiScore: item.aai_score,
    signal: deriveSignal(item.aai_score),
  };
}

function mapBackendList(w) {
  return {
    id: w.id,
    name: w.name,
    createdAt: w.created_at,
    items: (w.items || []).map(mapBackendItem),
  };
}

export const watchlistApi = {
  getEmptyState: () => watchlistsData.emptyState,

  getInitialLists: () => {
    if (USE_MOCK) {
      return watchlistsData.lists.map((l) => ({
        id: l.id,
        name: l.name,
        createdAt: l.createdAt,
        items: l.items.map(enrichRawItem),
      }));
    }
    // Sync wrapper kept for call-site compatibility (WatchlistsPage seeds
    // initial state with this) — actual fetch happens via getInitialListsAsync.
    return [];
  },

  getInitialListsAsync: async () => {
    if (USE_MOCK) {
      return watchlistsData.lists.map((l) => ({
        id: l.id,
        name: l.name,
        createdAt: l.createdAt,
        items: l.items.map(enrichRawItem),
      }));
    }
    const lists = await apiFetch("/watchlists");
    return lists.map(mapBackendList);
  },

  getSearchableItems: () => ALL_ITEMS,

  buildListItemFromDiscoverItem: (discoverItem) => enrichRawItem(rawFromDiscoverItem(discoverItem)),

  // ── mutations ──────────────────────────────────────────────────────────

  createList: async (name) => {
    if (USE_MOCK) return { id: `wl_${Date.now()}` };
    return apiFetch("/watchlists", { method: "POST", body: JSON.stringify({ name }) });
  },

  deleteList: async (watchlistId) => {
    if (USE_MOCK) return null;
    return apiFetch(`/watchlists/${watchlistId}`, { method: "DELETE" });
  },

  addItem: async (watchlistId, type, symbolOrSlug) => {
    if (USE_MOCK) return { status: "added" };
    return apiFetch(`/watchlists/${watchlistId}/items`, {
      method: "POST",
      body: JSON.stringify({ type, symbol_or_slug: symbolOrSlug }),
    });
  },

  removeItem: async (watchlistId, symbolOrSlug) => {
    if (USE_MOCK) return null;
    return apiFetch(`/watchlists/${watchlistId}/items/${symbolOrSlug}`, { method: "DELETE" });
  },
};