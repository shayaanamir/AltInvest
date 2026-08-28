import assetsData from "../data/sample_data/assets.json";
import nftData from "../data/sample_data/nftCollections.json";

const SIM_DELAY = 300;
function delay(fn) {
  return new Promise((resolve) => setTimeout(() => resolve(fn()), SIM_DELAY));
}

function normaliseCrypto(a) {
  const riskScore = a.risk?.score ?? 50;
  return {
    id: a.symbol,
    type: "crypto",
    symbol: a.symbol,
    name: a.name,
    subtitle: a.subcategory,
    avatarColor: a.logoColor,
    price: a.price,
    priceLabel: null,
    change24h: a.change24h ?? 0,
    aaiScore: a.aai?.score ?? null,
    aaiSignal: a.aai?.signal ?? null,
    riskScore,
    volatility: Math.round(100 - riskScore),
    expectedReturn: a.prediction?.prediction30dPct ?? 0,
    sentimentScore: a.sentiment?.score ?? 0,
    sentimentConfidence: a.sentiment?.confidence ?? 0.5,
    sentimentConfidenceLabel: a.sentiment?.confidenceLabel ?? "medium",
    sentimentTrend: a.sentiment?.trend ?? "stable",
    held: !!a.held,
    watching: !!a.watching,
  };
}

function normaliseNft(c) {
  const illiquidity = c.liquidity?.illiquidityRiskScore ?? 50;
  const expectedReturn =
    c.prediction?.prophetFloor30dEth && c.floorEth
      ? Math.round(((c.prediction.prophetFloor30dEth - c.floorEth) / c.floorEth) * 1000) / 10
      : 0;
  return {
    id: c.slug,
    type: "nft",
    symbol: c.symbol,
    name: c.name,
    subtitle: c.subcategory,
    avatarColor: c.bannerColor,
    price: c.floorUsd,
    priceLabel: c.floorEth != null ? `${c.floorEth.toFixed(2)} ETH` : null,
    change24h: c.change24h ?? 0,
    aaiScore: c.aai?.score ?? null,
    aaiSignal: c.aai?.signal ?? null,
    riskScore: Math.round(100 - illiquidity),
    volatility: Math.round(illiquidity),
    expectedReturn,
    sentimentScore: c.sentiment?.score ?? 0,
    sentimentConfidence: c.sentiment?.confidence ?? 0.5,
    sentimentConfidenceLabel: c.sentiment?.confidenceLabel ?? "medium",
    sentimentTrend: c.sentiment?.trend ?? "stable",
    held: !!c.held,
    watching: !!c.watching,
  };
}

let _universe = null;
function buildUniverse() {
  if (_universe) return _universe;
  const crypto = assetsData.assets.map(normaliseCrypto);
  const nft = nftData.collections.map(normaliseNft);
  _universe = [...crypto, ...nft];
  return _universe;
}

export function sentimentReadLabel(score) {
  if (score >= 0.5) return "Strongly bullish";
  if (score >= 0.2) return "Bullish";
  if (score > -0.2) return "Neutral";
  if (score > -0.5) return "Bearish";
  return "Strongly bearish";
}

export function evidenceLabel(confidenceLabel) {
  if (confidenceLabel === "high") return "well corroborated";
  if (confidenceLabel === "medium") return "moderately corroborated";
  return "thin evidence";
}

export const compareApi = {
  getUniverse: async () => delay(() => buildUniverse()),

  getByIds: async (ids) =>
    delay(() => {
      const universe = buildUniverse();
      return ids.map((id) => universe.find((a) => a.id === id)).filter(Boolean);
    }),

  search: async (query) =>
    delay(() => {
      const universe = buildUniverse();
      const q = query.trim().toLowerCase();
      if (!q) return universe;
      return universe.filter(
        (a) => a.name.toLowerCase().includes(q) || a.symbol.toLowerCase().includes(q)
      );
    }),
};