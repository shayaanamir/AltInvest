import discoverConfig from "../data/sample_data/discover.json";
import { ALL_ITEMS, CRYPTO_ITEMS, NFT_ITEMS } from "./assetRepository";

export { ALL_ITEMS, CRYPTO_ITEMS, NFT_ITEMS };

const SORTERS = {
  aai_desc: (a, b) => b.aaiScore - a.aaiScore,
  aai_asc: (a, b) => a.aaiScore - b.aaiScore,
  change24h_desc: (a, b) => b.changePct - a.changePct,
  change24h_asc: (a, b) => a.changePct - b.changePct,
  marketCap_desc: (a, b) => b.marketCap - a.marketCap,
  name_asc: (a, b) => a.name.localeCompare(b.name),
};

export const discoverApi = {
  getConfig: async () => discoverConfig,

  getItems: async (category, filters) => {
    let items =
      category === "crypto" ? CRYPTO_ITEMS :
      category === "nft" ? NFT_ITEMS :
      ALL_ITEMS;

    if (filters) {
      items = items.filter((it) => {
        if (filters.minAai != null && it.aaiScore < filters.minAai) return false;
        if (filters.minSentiment != null && it.sentimentScore * 100 < filters.minSentiment) return false;
        if (filters.maxVolatility != null && it.volatility > filters.maxVolatility) return false;
        if (filters.minMarketCap != null && it.marketCap < filters.minMarketCap) return false;
        return true;
      });

      const sorter = SORTERS[filters.sortBy] || SORTERS.aai_desc;
      items = [...items].sort(sorter);
    }

    return items;
  },
};