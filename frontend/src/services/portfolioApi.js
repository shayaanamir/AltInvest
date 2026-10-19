import { apiFetch } from "./apiClient";
import { fetchUniverse } from "./assetRepository";

function round2(n) {
  return Math.round(n * 100) / 100;
}

// ── real-data mappers ───────────────────────────────────────────────────────
// Holdings come from /portfolio/holdings. Names, colours, 24h change and the AAI read
// come from the same covered-universe rows Discover uses (GET /discover), so they are
// database values too. A holding whose asset isn't covered keeps its own stored fields.

const SIGNAL_TO_ACTION = { BUY: "Buy More", HOLD: "Hold", SELL: "Reduce" };

function mapCryptoHolding(h, meta) {
  const costBasis = h.cost_basis_usd || 0;
  const currentValue = h.current_value_usd || 0;
  return {
    id: h.id,
    symbol: h.symbol,
    name: h.name || meta?.name || h.symbol,
    logoColor: meta?.color || "var(--sv2-accent)",
    quantity: h.quantity,
    valueUsd: currentValue,
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
  const currentValueUsd = h.current_value_usd || 0;
  const floorEth = meta?.floorEth ?? null;
  return {
    id: h.id,
    collectionSlug: h.nft_collection_slug,
    collectionName: meta?.name || h.name || h.nft_collection_slug,
    tokenId: h.nft_token_id,
    quantity: h.quantity,
    avgBuyPriceEth: h.avg_buy_price_eth ?? null,
    currentPriceEth: floorEth,
    valueUsd: currentValueUsd,
    costBasisUsd: costBasis,
    changePct: costBasis > 0 ? round2(((currentValueUsd - costBasis) / costBasis) * 100) : 0,
    aiAction: meta?.signal ? SIGNAL_TO_ACTION[meta.signal] || "Hold" : "Hold",
    artColor: meta?.color || "#c9805a",
    dateAdded: h.date_added,
  };
}

let _cachedHoldings = null; // per-mount cache so getCryptoHoldings/getNftHoldings/getSummary don't triple-fetch
async function fetchAllHoldings() {
  if (_cachedHoldings) return _cachedHoldings;
  _cachedHoldings = await apiFetch("/portfolio/holdings");
  return _cachedHoldings;
}
export function invalidateHoldingsCache() {
  _cachedHoldings = null;
}

async function fetchUniverseById() {
  const rows = await fetchUniverse({ category: "all" });
  return new Map(rows.map((r) => [r.id, r]));
}

export const portfolioApi = {
  getSummary: async () => {
    const s = await apiFetch("/portfolio/summary");
    return {
      totalBalance: s.total_value_usd,
      totalCostBasis: s.total_cost_basis_usd,
      totalProfitLoss: s.total_unrealised_pnl_usd,
      totalProfitLossPct: s.total_unrealised_pnl_pct ?? 0,
      totalProfitLossPositive: s.total_unrealised_pnl_usd >= 0,
      positionsCount: s.holding_count,
      // Diversification isn't computed server-side yet (no
      // /portfolio/intelligence route) — placeholder until it exists.
      diversificationScore: 50,
      diversificationLabel: "Not yet available",
      needsRebalancing: false,
      rebalanceNote: "Rebalancing insights are coming soon.",
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

  // No /portfolio/intelligence route exists yet, so this is computed here from the user's
  // holdings and the stored signal / sentiment / risk of each held asset.
  getIntelligence: async () => {
    const [holdings, universe] = await Promise.all([fetchAllHoldings(), fetchUniverseById().catch(() => new Map())]);
    const cryptoHoldings = holdings.filter((h) => h.asset_type === "crypto");
    const signalMix = {};
    let sentimentSum = 0;
    let sentimentCount = 0;
    let riskSum = 0;
    let riskCount = 0;

    cryptoHoldings.forEach((h) => {
      const meta = universe.get(h.symbol);
      if (meta?.signal) {
        const label = { BUY: "Buy", HOLD: "Hold", SELL: "Sell" }[meta.signal] || "Hold";
        signalMix[label] = (signalMix[label] || 0) + 1;
      }
      if (meta?.sentimentScore != null) {
        sentimentSum += meta.sentimentScore;
        sentimentCount += 1;
      }
      if (meta?.riskScore != null) {
        riskSum += meta.riskScore;
        riskCount += 1;
      }
    });

    const suggestions = [];
    if (holdings.length === 0) {
      suggestions.push("No holdings yet — add assets to your portfolio to view risk, sentiment, and AI signal breakdown.");
    } else if (cryptoHoldings.length === 0) {
      suggestions.push("Only NFT holdings detected — add crypto assets to compute risk volatility and sentiment exposure.");
    } else {
      suggestions.push("Portfolio intelligence is computed from the stored scores of the assets you hold.");
    }

    return {
      aggregateRiskScore: riskCount ? Math.round(riskSum / riskCount) : null,
      sentimentExposure: sentimentCount ? round2(sentimentSum / sentimentCount) : null,
      signalMix,
      suggestions,
      concentrated: false,
    };
  },

  addHolding: (payload) => {
    // payload shape matches backend/models/schemas.py::PortfolioHoldingIn
    // e.g. { asset_type: "crypto", symbol: "SOL", quantity: 2.5,
    //        avg_buy_price_usd: 150, cost_basis_usd: 375 }
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
