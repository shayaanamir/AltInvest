import { apiFetch } from "./apiClient";
import { fetchUniverse } from "./assetRepository";
import { notifyHoldingsChanged } from "./holdingsEvents";
import { getToken } from "../hooks/useAuth";

function round2(n) {
  return Math.round(n * 100) / 100;
}

// ── real-data mappers ───────────────────────────────────────────────────────
// Holdings come from /portfolio/holdings. Names, colours, 24h change and the AAI read
// come from the same covered-universe rows Discover uses (GET /discover), so they are
// database values too. A holding whose asset isn't covered keeps its own stored fields.

const SIGNAL_TO_ACTION = { BUY: "Buy More", HOLD: "Hold", SELL: "Reduce" };

// A holding the server couldn't value (no market price yet) comes back with no value, not 0.
// Treat it as unpriced everywhere, so it isn't shown as worth nothing or as a total loss.
const isPriced = (h) => (h.valuation_status ? h.valuation_status === "ok" : h.current_value_usd != null);

function mapCryptoHolding(h, meta) {
  const costBasis = h.cost_basis_usd || 0;
  const priced = isPriced(h);
  const currentValue = priced ? h.current_value_usd : null;
  return {
    id: h.id,
    symbol: h.symbol,
    name: h.name || meta?.name || h.symbol,
    logoColor: meta?.color || "var(--sv2-accent)",
    quantity: h.quantity,
    avgBuyPriceUsd: h.avg_buy_price_usd ?? null,
    valueUsd: currentValue,
    priced,
    costBasisUsd: costBasis,
    // Per-holding 24h P&L isn't computed server-side; the asset's own market change is the closest stored signal.
    change24hPct: meta?.change24h ?? 0,
    aaiScore: meta?.aaiScore ?? null,
    aiAction: meta?.signal ? SIGNAL_TO_ACTION[meta.signal] || "Hold" : "Hold",
    dateAdded: h.date_added,
  };
}

function mapNftHolding(h, meta) {
  const costBasis = h.cost_basis_usd || 0;
  const priced = isPriced(h);
  const currentValueUsd = priced ? h.current_value_usd : null;
  const floorEth = meta?.floorEth ?? null;
  return {
    id: h.id,
    collectionSlug: h.nft_collection_slug,
    collectionName: meta?.name || h.name || h.nft_collection_slug,
    tokenId: h.nft_token_id,
    quantity: h.quantity,
    avgBuyPriceEth: h.avg_buy_price_eth ?? null,
    ethUsdRateAtBuy: h.avg_buy_eth_usd_rate ?? null,
    currentPriceEth: floorEth,
    valueUsd: currentValueUsd,
    priced,
    costBasisUsd: costBasis,
    changePct: priced && costBasis > 0 ? round2(((currentValueUsd - costBasis) / costBasis) * 100) : 0,
    aaiScore: meta?.aaiScore ?? null,
    aiAction: meta?.signal ? SIGNAL_TO_ACTION[meta.signal] || "Hold" : "Hold",
    artColor: meta?.color || "#c9805a",
    dateAdded: h.date_added,
  };
}

// Per-mount cache so getCryptoHoldings/getNftHoldings/getSummary don't triple-fetch. It belongs to the
// token it was fetched with, so after logout, account deletion or another sign-in it is never reused.
let _cachedHoldings = null;
let _cachedForToken = null;
async function fetchAllHoldings() {
  const token = getToken();
  if (_cachedHoldings && _cachedForToken === token) return _cachedHoldings;
  const rows = await apiFetch("/portfolio/holdings");
  _cachedHoldings = rows;
  _cachedForToken = token;
  return rows;
}
// Called after every successful add / edit / remove: drops the cache and tells open screens to reload.
export function invalidateHoldingsCache() {
  _cachedHoldings = null;
  notifyHoldingsChanged();
}

async function fetchUniverseById() {
  const rows = await fetchUniverse({ category: "all" });
  return new Map(rows.map((r) => [r.id, r]));
}

// One request serves both the summary card and the intelligence panel.
let _intelPromise = null;
function fetchIntelligence() {
  if (!_intelPromise) {
    _intelPromise = apiFetch("/portfolio/intelligence").finally(() => {
      setTimeout(() => { _intelPromise = null; }, 0);
    });
  }
  return _intelPromise;
}

export const portfolioApi = {
  getSummary: async () => {
    const [s, intel] = await Promise.all([apiFetch("/portfolio/summary"), fetchIntelligence()]);
    return {
      totalBalance: s.total_value_usd,
      totalCostBasis: s.total_cost_basis_usd,
      totalProfitLoss: s.total_unrealised_pnl_usd,
      totalProfitLossPct: s.total_unrealised_pnl_pct ?? 0,
      totalProfitLossPositive: s.total_unrealised_pnl_usd >= 0,
      positionsCount: s.holding_count,
      unpricedCount: s.unpriced_holding_count ?? 0, // holdings with no price, left out of the totals above
      // From GET /portfolio/intelligence: 0-100 from the spread of position values (null with no priced holdings).
      diversificationScore: intel.diversification_score,
      diversificationLabel: intel.diversification_label,
      needsRebalancing: intel.concentrated,
      rebalanceNote: intel.largest_position
        ? `Largest position: ${intel.largest_position.name}, ${intel.largest_position.weight_pct}% of value.`
        : "",
    };
  },

  getPerformanceHistory: async (filter = "3M") => {
    const res = await apiFetch(`/portfolio/performance?filter=${encodeURIComponent(filter)}`);
    return (res.points || []).map((p) => ({ date: p.timestamp, value: p.value }));
  },

  getAllocation: async () => {
    const slices = await apiFetch("/portfolio/allocation?by=category");
    const LABELS = { crypto: "Crypto", nft: "NFTs" };
    return slices.map((s) => ({
      label: LABELS[s.label] || s.label,
      valueUsd: s.value_usd,
      pct: s.pct_of_portfolio,
    }));
  },

  getCryptoHoldings: async () => {
    const [holdings, universe] = await Promise.all([fetchAllHoldings(), fetchUniverseById().catch(() => new Map())]);
    return holdings.filter((h) => h.asset_type === "crypto").map((h) => mapCryptoHolding(h, universe.get(h.symbol)));
  },

  getNftHoldings: async () => {
    const [holdings, universe] = await Promise.all([fetchAllHoldings(), fetchUniverseById().catch(() => new Map())]);
    return holdings
      .filter((h) => h.asset_type === "nft")
      .map((h) => mapNftHolding(h, universe.get(h.nft_collection_slug)));
  },

  // Computed on the server (GET /portfolio/intelligence), weighted by each position's current value.
  getIntelligence: async () => {
    const i = await fetchIntelligence();
    const LABELS = { BUY: "Buy", HOLD: "Hold", SELL: "Sell" };
    const signalMix = {};
    Object.entries(i.signal_mix || {}).forEach(([k, n]) => {
      signalMix[LABELS[k] || k] = n;
    });
    return {
      aggregateRiskScore: i.aggregate_risk_score,
      sentimentExposure: i.sentiment_exposure != null ? round2(i.sentiment_exposure) : null,
      signalMix,
      suggestions: i.suggestions || [],
      concentrated: i.concentrated,
      diversificationScore: i.diversification_score,
      largestPosition: i.largest_position,
    };
  },

  // A holding's history: buys, sells, corrections, removal.
  getTransactions: (holdingId) => apiFetch(`/portfolio/holdings/${holdingId}/transactions`),

  // Buy more of / sell some of a crypto holding. Resolves with { quantity, closed, realised_pnl_usd }.
  recordTrade: (holdingId, { type, quantity, price_usd }) =>
    apiFetch(`/portfolio/holdings/${holdingId}/transactions`, {
      method: "POST",
      body: JSON.stringify({ type, quantity, price_usd }),
    }).then((res) => {
      invalidateHoldingsCache();
      return res;
    }),

  addHolding: (payload) => {
    // payload shape matches backend/models/schemas.py::PortfolioHoldingIn
    // e.g. { asset_type: "crypto", symbol: "SOL", quantity: 2.5, avg_buy_price_usd: 150 }
    // The server works out the cost basis, and merges into an existing holding of the same asset
    // (the response then has merged: true).
    return apiFetch("/portfolio/holdings", {
      method: "POST",
      body: JSON.stringify(payload),
    }).then((res) => {
      invalidateHoldingsCache();
      return res;
    });
  },

  updateHolding: (holdingId, patch) =>
    apiFetch(`/portfolio/holdings/${holdingId}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }).then((res) => {
      invalidateHoldingsCache();
      return res;
    }),

  removeHolding: (holdingId) =>
    apiFetch(`/portfolio/holdings/${holdingId}`, { method: "DELETE" }).then((res) => {
      invalidateHoldingsCache();
      return res;
    }),
};
