import assetsData from "../data/sample_data/assets.json";
import nftData from "../data/sample_data/nftCollections.json";
import assetDetailData from "../data/sample_data/assetDetail.json";
import nftDetailData from "../data/sample_data/nftDetail.json";

export const CRYPTO_ITEMS = assetsData.assets.map((a) => ({
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

export const NFT_ITEMS = nftData.collections.map((c) => ({
  id: c.slug,
  type: "nft",
  symbol: c.symbol,
  name: c.name,
  subcategory: c.subcategory,
  color: c.bannerColor,
  price: c.floorUsd,
  changePct: c.change24h,
  aaiScore: c.aai?.score,
  signal: c.aai?.signal,
  sentimentScore: c.sentiment?.score,
  volatility: c.liquidity?.illiquidityRiskScore ?? c.risk?.illiquidityRiskScore ?? c.risk?.volatilityIndex ?? 50,
  marketCap: c.marketCapUsd ?? (c.floorUsd && c.supply ? c.floorUsd * c.supply : 0),
  held: c.held,
  watching: c.watching,
  sparkline: (nftDetailData[c.slug]?.floorHistory || []).map((p) => p.floorEth ?? p.floorUsd ?? p.price ?? 0),
}));

export const ALL_ITEMS = [...CRYPTO_ITEMS, ...NFT_ITEMS];

