import { USE_MOCK } from "../config";
import { apiFetch } from "./apiClient";
import portfolioData from "../data/sample_data/portfolio.json";
import assetsData from "../data/sample_data/assets.json";
import nftCollectionsData from "../data/sample_data/nftCollections.json";

const SIM_DELAY = 400;
function delay(fn) {
  return new Promise((resolve) => setTimeout(() => resolve(fn()), SIM_DELAY));
}

function round2(n) {
  return Math.round(n * 100) / 100;
}

// ── mock helpers (unchanged behaviour when USE_MOCK=true) ──────────────────

function computeTotals() {
  const { cryptoHoldings, nftHoldings } = portfolioData;
  const cryptoValue = cryptoHoldings.reduce((s, h) => s + h.valueUsd, 0);
  const nftValue = nftHoldings.reduce((s, h) => s + h.valueUsd, 0);
  const cryptoCost = cryptoHoldings.reduce((s, h) => s + h.costBasisUsd, 0);
  const nftCost = nftHoldings.reduce((s, h) => s + h.costBasisUsd, 0);

  const totalBalance = cryptoValue + nftValue;
  const totalCostBasis = cryptoCost + nftCost;
  const totalProfitLoss = totalBalance - totalCostBasis;
  const totalProfitLossPct = totalCostBasis > 0 ? (totalProfitLoss / totalCostBasis) * 100 : 0;
  const positionsCount = cryptoHoldings.length + nftHoldings.length;

  return { totalBalance, totalCostBasis, totalProfitLoss, totalProfitLossPct, positionsCount, cryptoValue, nftValue };
}

function countSignals() {
  const holdings = [...portfolioData.cryptoHoldings, ...portfolioData.nftHoldings];
  const counts = {};
  holdings.forEach((h) => {
    const key = (h.aiAction || "Hold").replace(" More", "");
    counts[key] = (counts[key] || 0) + 1;
  });
  return counts;
}

// ── real-data mappers ───────────────────────────────────────────────────────

function assetMetaFor(symbol) {
  return assetsData.assets.find((a) => a.symbol === symbol);
}

function nftMetaFor(slug) {
  return nftCollectionsData.collections.find((c) => c.slug === slug);
}

function mapCryptoHolding(h) {
  const meta = assetMetaFor(h.symbol);
  const costBasis = h.cost_basis_usd || 0;
  const currentValue = h.current_value_usd || 0;
  return {
    id: h.id,
    symbol: h.symbol,
    name: h.name || meta?.name || h.symbol,
    logoColor: meta?.logoColor || "var(--sv2-accent)",
    quantity: h.quantity,
    valueUsd: currentValue,
    costBasisUsd: costBasis,
    change24hPct: meta?.change24h ?? 0, // per-holding 24h P&L isn't computed server-side yet — using the asset's market change as the closest available signal
    aaiScore: meta?.aai?.score ?? null,
    aiAction: meta?.aai?.signal
      ? { BUY: "Buy More", HOLD: "Hold", SELL: "Reduce" }[meta.aai.signal] || "Hold"
      : "Hold",
    dateAdded: h.date_added,
  };
}

function mapNftHolding(h) {
  const meta = nftMetaFor(h.nft_collection_slug);
  const costBasis = h.cost_basis_usd || 0;
  const currentValueUsd = h.current_value_usd || 0;
  const currentPriceEth = meta?.floorEth ?? null;
  return {
    collectionSlug: h.nft_collection_slug,
    collectionName: meta?.name || h.nft_collection_slug,
    tokenId: h.nft_token_id,
    quantity: h.quantity,
    avgBuyPriceEth: h.avg_buy_price_eth ?? null,
    currentPriceEth,
    valueUsd: currentValueUsd,
    costBasisUsd: costBasis,
    changePct: costBasis > 0 ? round2(((currentValueUsd - costBasis) / costBasis) * 100) : 0,
    aiAction: "Hold",
    artColor: meta?.bannerColor || "#c9805a",
    dateAdded: h.date_added,
  };
}

let _cachedHoldings = null; // per-mount cache so getCryptoHoldings/getNftHoldings/getSummary don't triple-fetch
async function fetchAllHoldings() {
  if (_cachedHoldings) return _cachedHoldings;
  _cachedHoldings = await apiFetch("/portfolio/holdings");
  return _cachedHoldings;
}
function invalidateHoldingsCache() {
  _cachedHoldings = null;
}

export const portfolioApi = {
  getSummary: () => {
    if (USE_MOCK) {
      return delay(() => {
        const totals = computeTotals();
        const { summary } = portfolioData;
        return {
          totalBalance: round2(totals.totalBalance),
          totalCostBasis: round2(totals.totalCostBasis),
          totalProfitLoss: round2(totals.totalProfitLoss),
          totalProfitLossPct: round2(totals.totalProfitLossPct),
          totalProfitLossPositive: totals.totalProfitLoss >= 0,
          positionsCount: totals.positionsCount,
          diversificationScore: summary.diversificationScore,
          diversificationLabel: summary.diversificationLabel,
          needsRebalancing: summary.needsRebalancing,
          rebalanceNote: summary.needsRebalancing ? summary.rebalanceNote : summary.balancedNote,
        };
      });
    }
    return (async () => {
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
    })();
  },

  getPerformanceHistory: (filter = "3M") => {
    if (USE_MOCK) return delay(() => portfolioData.performanceHistory[filter] || []);
    return (async () => {
      const res = await apiFetch(`/portfolio/performance?filter=${encodeURIComponent(filter)}`);
      return (res.points || []).map((p) => ({ date: p.timestamp, value: p.value }));
    })();
  },

  getAllocation: () => {
    if (USE_MOCK) {
      return delay(() => {
        const totals = computeTotals();
        const total = totals.totalBalance || 1;
        const rows = [
          { label: "Crypto", valueUsd: totals.cryptoValue, pct: (totals.cryptoValue / total) * 100 },
          { label: "NFTs", valueUsd: totals.nftValue, pct: (totals.nftValue / total) * 100 },
        ];
        return rows.filter((r) => r.valueUsd > 0);
      });
    }
    return (async () => {
      const slices = await apiFetch("/portfolio/allocation?by=category");
      const LABELS = { crypto: "Crypto", nft: "NFTs" };
      return slices.map((s) => ({
        label: LABELS[s.label] || s.label,
        valueUsd: s.value_usd,
        pct: s.pct_of_portfolio,
      }));
    })();
  },

  getCryptoHoldings: () => {
    if (USE_MOCK) return delay(() => portfolioData.cryptoHoldings);
    return (async () => {
      const holdings = await fetchAllHoldings();
      return holdings.filter((h) => h.asset_type === "crypto").map(mapCryptoHolding);
    })();
  },

  getNftHoldings: () => {
    if (USE_MOCK) return delay(() => portfolioData.nftHoldings);
    return (async () => {
      const holdings = await fetchAllHoldings();
      return holdings.filter((h) => h.asset_type === "nft").map(mapNftHolding);
    })();
  },

  getIntelligence: () => {
    if (USE_MOCK) {
      return delay(() => {
        const { portfolioIntelligence, summary } = portfolioData;
        return {
          aggregateRiskScore: portfolioIntelligence.aggregateRiskScore,
          sentimentExposure: portfolioIntelligence.sentimentExposure,
          signalMix: countSignals(),
          suggestions: portfolioIntelligence.rebalancingSuggestions,
          concentrated: summary.needsRebalancing,
        };
      });
    }
    // No /portfolio/intelligence backend route exists yet — compute a
    // best-effort client-side version from real holdings + asset metadata
    // so the card isn't empty, and mark it clearly as partial.
    return (async () => {
      const holdings = await fetchAllHoldings();
      const cryptoHoldings = holdings.filter((h) => h.asset_type === "crypto");
      const signalMix = {};
      let sentimentSum = 0;
      let sentimentCount = 0;
      let riskSum = 0;
      let riskCount = 0;

      cryptoHoldings.forEach((h) => {
        const meta = assetMetaFor(h.symbol);
        if (meta?.aai?.signal) {
          const label = { BUY: "Buy", HOLD: "Hold", SELL: "Sell" }[meta.aai.signal] || "Hold";
          signalMix[label] = (signalMix[label] || 0) + 1;
        }
        if (meta?.sentiment?.score != null) {
          sentimentSum += meta.sentiment.score;
          sentimentCount += 1;
        }
        if (meta?.risk?.score != null) {
          riskSum += meta.risk.score;
          riskCount += 1;
        }
      });

      return {
        aggregateRiskScore: riskCount ? Math.round(riskSum / riskCount) : null,
        sentimentExposure: sentimentCount ? round2(sentimentSum / sentimentCount) : null,
        signalMix,
        suggestions: [
          "Portfolio intelligence (rebalancing suggestions) isn't computed server-side yet — this is a client-side approximation from held-asset metadata.",
        ],
        concentrated: false,
      };
    })();
  },

  addHolding: (payload) => {
    // payload shape matches backend/models/schemas.py::PortfolioHoldingIn
    // e.g. { asset_type: "crypto", symbol: "SOL", quantity: 2.5,
    //        avg_buy_price_usd: 150, cost_basis_usd: 375 }
    if (USE_MOCK) return delay(() => ({ id: `mock_${Date.now()}` }));
    return apiFetch("/portfolio/holdings", {
      method: "POST",
      body: JSON.stringify(payload),
    }).then((res) => {
      invalidateHoldingsCache();
      return res;
    });
  },

  updateHolding: (holdingId, patch) => {
    if (USE_MOCK) return delay(() => ({ status: "updated" }));
    return apiFetch(`/portfolio/holdings/${holdingId}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }).then((res) => {
      invalidateHoldingsCache();
      return res;
    });
  },

  removeHolding: (holdingId) => {
    if (USE_MOCK) return delay(() => null);
    return apiFetch(`/portfolio/holdings/${holdingId}`, { method: "DELETE" }).then((res) => {
      invalidateHoldingsCache();
      return res;
    });
  },
};