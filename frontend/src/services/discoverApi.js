import discoverConfig from "../content/discover.json";
import { apiFetch } from "./apiClient";
import { mapUniverseItem } from "./assetRepository";

/**
 * Discover talks to GET /discover in the backend's own terms: `sort` + `order` (keys published by
 * GET /discover/options, so the list can't drift), the backend's filter names, and limit/offset
 * paging with the match count from the X-Total-Count header.
 */

// A range filter is only sent once it differs from its default (the slider's open end), so
// unscored assets aren't excluded by a filter nobody touched.
function filterParams(f, ranges) {
  const p = new URLSearchParams();
  if (f.minAai > ranges.aaiScoreRange.min) p.set("min_aai", f.minAai);
  if (f.minSentiment > ranges.sentimentRange.min * 100) p.set("min_sentiment", f.minSentiment / 100);
  if (f.maxVolatility < ranges.volatilityRange.max) p.set("max_volatility", f.maxVolatility);
  if (f.maxRisk < ranges.riskRange.max) p.set("max_risk", f.maxRisk);
  if (f.minMarketCap > ranges.marketCapRange.min) p.set("min_market_cap", f.minMarketCap);
  f.subcategories.forEach((s) => p.append("subcategory", s));
  f.signals.forEach((s) => p.append("signal", s));
  if (f.verifiedOnly) p.set("verified_only", "true");
  if (f.heldOnly) p.set("held_only", "true");
  if (f.watchingOnly) p.set("watching_only", "true");
  return p;
}

export function defaultFilters() {
  const r = discoverConfig.filters;
  return {
    minAai: r.aaiScoreRange.min,
    minSentiment: r.sentimentRange.min * 100,
    maxVolatility: r.volatilityRange.max,
    maxRisk: r.riskRange.max,
    minMarketCap: r.marketCapRange.min,
    subcategories: [],
    signals: [],
    verifiedOnly: false,
    heldOnly: false,
    watchingOnly: false,
    sort: discoverConfig.defaultSort.key,
    order: discoverConfig.defaultSort.order,
  };
}

/** How many filters differ from their defaults (for the "Reset (3)" label). */
export function activeFilterCount(f) {
  const d = defaultFilters();
  return ["minAai", "minSentiment", "maxVolatility", "maxRisk", "minMarketCap", "verifiedOnly", "heldOnly", "watchingOnly"]
    .filter((k) => f[k] !== d[k]).length + f.subcategories.length + f.signals.length;
}

export const discoverApi = {
  // Tabs, slider ranges, page size and empty-state copy are UI configuration, not data.
  getConfig: async () => discoverConfig,

  /** Sort keys and the subcategories / signals that exist for this category, with counts. */
  getOptions: (category) => apiFetch(`/discover/options?category=${category === "nft" ? "nft" : "crypto"}`),

  /** One page: { items, total }. */
  getPage: async (category, filters, { q = "", offset = 0, limit = discoverConfig.pageSize } = {}) => {
    const p = filterParams(filters, discoverConfig.filters);
    p.set("category", category === "nft" ? "nft" : "crypto");
    p.set("sort", filters.sort);
    p.set("order", filters.order);
    if (q.trim()) p.set("q", q.trim().slice(0, 64));
    p.set("limit", limit);
    p.set("offset", offset);
    const { data, headers } = await apiFetch(`/discover?${p}`, { withHeaders: true });
    const total = Number(headers.get("X-Total-Count"));
    return { items: data.map(mapUniverseItem), total: Number.isFinite(total) ? total : data.length };
  },
};
