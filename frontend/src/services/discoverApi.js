import assetsData from "../data/sample_data/assets.json";
import nftData from "../data/sample_data/nftCollections.json";
import discoverConfig from "../data/sample_data/discover.json";
import assetDetailData from "../data/sample_data/assetDetail.json";
import nftDetailData from "../data/sample_data/nftDetail.json";

// Normalise crypto assets from assets.json, pulling sparkline history
// from assetDetail.json (priceHistory) so nothing is invented.
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

// Normalise NFT collections from nftCollections.json. There's no explicit
// "volatility" field for NFTs, so illiquidityRiskScore is used as the
// closest equivalent risk proxy for the volatility filter.
const NFT_ITEMS = nftData.collections.map((c) => ({
  id: c.slug,
  type: "nft",
  symbol: c.symbol,
  name: c.name,
  subcategory: c.subcategory,
  color: c.bannerColor,
  price: c.floorUsd,
  changePct: c.change24h,
  aaiScore: c.aai.score,
  signal: c.aai.signal,
  sentimentScore: c.sentiment.score,
  volatility: c.liquidity.illiquidityRiskScore,
  marketCap: c.floorUsd * c.supply,
  held: c.held,
  watching: c.watching,
  sparkline: (nftDetailData[c.slug]?.floorHistory || []).map((p) => p.floorEth),
}));

export const ALL_ITEMS = [...CRYPTO_ITEMS, ...NFT_ITEMS];

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