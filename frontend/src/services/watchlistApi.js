import watchlistsData from "../data/sample_data/watchlists.json";
import { ALL_ITEMS } from "./discoverApi";

function findMatch(raw) {
  if (raw.type === "crypto") return ALL_ITEMS.find((a) => a.type === "crypto" && a.symbol === raw.symbol);
  return ALL_ITEMS.find((a) => a.type === "nft" && a.id === raw.slug);
}

// watchlists.json doesn't carry a "signal" field for its items, so when a
// live match isn't available we derive one from the same score bands used
// elsewhere in the app (AssetIntelligence.jsx, sentimentApi.js).
function deriveSignal(score) {
  if (score == null) return null;
  if (score >= 65) return "BUY";
  if (score >= 45) return "HOLD";
  return "SELL";
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

export const watchlistApi = {
  getEmptyState: () => watchlistsData.emptyState,

  getInitialLists: () =>
    watchlistsData.lists.map((l) => ({
      id: l.id,
      name: l.name,
      createdAt: l.createdAt,
      items: l.items.map(enrichRawItem),
    })),

  // Powers the "Starter assets" search in the create-watchlist modal.
  getSearchableItems: () => ALL_ITEMS,

  buildListItemFromDiscoverItem: (discoverItem) => enrichRawItem(rawFromDiscoverItem(discoverItem)),
};