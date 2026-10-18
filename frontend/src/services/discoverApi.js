import discoverConfig from "../data/sample_data/discover.json";
import { fetchUniverse } from "./assetRepository";

// UI-sort key -> backend sort / order
const SORTS = {
  aai_desc: { sort: "aai_score", order: "desc" },
  aai_asc: { sort: "aai_score", order: "asc" },
  change24h_desc: { sort: "change_24h", order: "desc" },
  change24h_asc: { sort: "change_24h", order: "asc" },
  marketCap_desc: { sort: "market_cap", order: "desc" },
  name_asc: { sort: "name", order: "asc" },
};

// A range filter is only sent once it differs from its default (the slider's
// open end), so unscored assets aren't excluded by a filter nobody touched.
function activeFilterParams(filters, ranges) {
  const p = {};
  if (filters.minAai > ranges.aaiScoreRange.min) p.min_aai = filters.minAai;
  if (filters.minSentiment > ranges.sentimentRange.min * 100) p.min_sentiment = filters.minSentiment / 100;
  if (filters.maxVolatility < ranges.volatilityRange.max) p.max_volatility = filters.maxVolatility;
  if (filters.minMarketCap > ranges.marketCapRange.min) p.min_market_cap = filters.minMarketCap;
  return p;
}

export const discoverApi = {
  // Tabs, sort options, slider ranges and empty-state copy are UI configuration, not data.
  getConfig: async () => discoverConfig,

  getItems: (category, filters) => {
    const sort = SORTS[filters?.sortBy] || SORTS.aai_desc;
    return fetchUniverse({
      category: category === "crypto" || category === "nft" ? category : "all",
      ...sort,
      ...(filters ? activeFilterParams(filters, discoverConfig.filters) : {}),
    });
  },
};
