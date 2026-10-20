import { apiFetch } from "./apiClient";

// Maps one row of the backend's unified universe (GET /discover) to the shape
// the Discover and Compare UI reads. Fields the database has no value for
// stay null — nothing is filled in here.
export function mapUniverseItem(r) {
  const nft = r.category === "nft";
  return {
    id: r.id,
    type: r.category,
    category: r.category,
    symbol: r.symbol,
    name: r.name,
    subcategory: r.subcategory,
    subtitle: r.subcategory,
    color: r.logo_color,
    avatarColor: r.logo_color,
    price: r.price,
    priceLabel: nft && r.floor_eth != null ? `${r.floor_eth.toFixed(2)} ETH` : null,
    floorEth: r.floor_eth ?? null,
    changePct: r.change_24h,
    change24h: r.change_24h,
    change7d: r.change_7d,
    marketCap: r.market_cap,
    volume24h: r.volume_24h,
    aaiScore: r.aai_score,
    signal: r.signal,
    aaiSignal: r.signal,
    riskScore: r.risk_score,
    volatility: r.volatility,
    expectedReturn: r.expected_return,
    sentimentScore: r.sentiment_score,
    sentimentConfidence: r.sentiment_confidence,
    sentimentConfidenceLabel: r.sentiment_confidence_label,
    sentimentTrend: r.sentiment_trend,
    verified: r.verified,
    held: !!r.held,
    watching: !!r.watching,
    sparkline: r.sparkline || [],
  };
}

/** GET /discover — `params` are the backend's query params (undefined values are dropped). */
export async function fetchUniverse(params = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  });
  const rows = await apiFetch(`/discover${qs.toString() ? `?${qs}` : ""}`);
  return rows.map(mapUniverseItem);
}

/**
 * The covered-universe row for one crypto symbol, including whether the signed-in user holds it
 * and watches it. Resolves to null when the symbol isn't in the covered universe.
 */
export async function fetchAssetStatus(symbol) {
  const rows = await fetchUniverse({ category: "crypto", q: symbol });
  return rows.find((r) => r.symbol?.toUpperCase() === symbol.toUpperCase()) || null;
}
