import { apiFetch } from "./apiClient";
import { mapItemValue } from "../utils/nftItemValue";

// NFT collection page data (Phase 10, ml/docs/DECISIONS.md D61, D67): GET /nft/collections/{slug} on the backend,
// which stores what the ML service serves (daily floor, liquidity, floor volatility and the NFT risk score).

function mapRisk(d) {
  const liq = d.liquidity || {};
  return {
    volatility: typeof d.volatility === "number" ? d.volatility : null,
    riskScore: typeof d.risk_score === "number" ? d.risk_score : null,
    note: d.risk_note || "",
    modelVersion: d.risk_model_version || null,
    asOf: d.risk_as_of || null,
    lastUpdated: d.last_updated || null,
    isIlliquid: liq.source === "ml-service" ? liq.is_illiquid === true : null,
  };
}

function mapLiquidity(l) {
  if (!l || l.source !== "ml-service") return null;
  return {
    score: l.liquidity_score, label: l.label, isIlliquid: l.is_illiquid === true, sales7d: l.sales_7d,
    sales30d: l.sales_30d, volume7dEth: l.volume_7d_eth, volume30dEth: l.volume_30d_eth,
    washShare30d: l.wash_removed_share_30d, marketplaces: l.marketplaces_counted, asOf: l.date,
  };
}

export const nftApi = {
  /** Item estimate (Phase 10 step 10.7, D78). Resolves to null for an unknown token (404); throws otherwise. */
  getItemValue: async (slug, tokenId) => {
    try {
      return mapItemValue(await apiFetch(`/nft/collections/${encodeURIComponent(slug)}/items/${encodeURIComponent(tokenId)}/value`));
    } catch (e) {
      if (e.status === 404) return null;
      throw e;
    }
  },
  /** Resolves to null when the backend has no such collection (404); throws on any other failure. */
  getCollection: async (slug) => {
    let d;
    try {
      d = await apiFetch(`/nft/collections/${encodeURIComponent(slug)}`);
    } catch (e) {
      if (e.status === 404) return null;
      throw e;
    }
    const m = d.market || {};
    return {
      slug: d.slug,
      name: d.name,
      symbol: d.symbol,
      verified: d.verified,
      supply: d.supply,
      subcategory: d.subcategory,
      bannerColor: d.banner_color,
      floorEth: m.floor_eth ?? null,
      floorUsd: m.floor_usd ?? null,
      change24h: m.change_24h ?? null,
      change7d: m.change_7d ?? null,
      floorDate: m.date ?? null,
      history: d.floor_history || [],
      risk: mapRisk(d),
      liquidity: mapLiquidity(d.liquidity),
      recentSales: (d.recent_sales || []).map((s) => ({
        tokenId: s.token_id, timestamp: s.timestamp, priceEth: s.price_eth, priceUsd: s.price_usd,
        marketplace: s.marketplace,
      })),
    };
  },
};
