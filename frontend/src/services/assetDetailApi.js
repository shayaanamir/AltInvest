import assetDetailData from "../data/sample_data/assetDetail.json";
import assetsData from "../data/sample_data/assets.json";
import portfolioData from "../data/sample_data/portfolio.json";

const SIM_DELAY = 350;
function delay(fn) {
  return new Promise((resolve) => setTimeout(() => resolve(fn()), SIM_DELAY));
}

function findHolding(symbol) {
  return portfolioData.cryptoHoldings.find((h) => h.symbol === symbol) || null;
}

function findAssetMeta(symbol) {
  return assetsData.assets.find((a) => a.symbol === symbol) || null;
}

// Same score bands used elsewhere in the app (see landingPage/ScoreShowcase.jsx)
export function deriveAaiSignal(score) {
  if (score == null) return { label: "Hold", tone: "neutral" };
  if (score >= 75) return { label: "Strong Buy", tone: "positive" };
  if (score >= 55) return { label: "Buy", tone: "positive" };
  if (score >= 45) return { label: "Hold", tone: "neutral" };
  if (score >= 25) return { label: "Sell", tone: "negative" };
  return { label: "Strong Sell", tone: "negative" };
}

export function confidenceLabel(pct) {
  if (pct >= 70) return "well corroborated";
  if (pct >= 40) return "fairly supported";
  return "thin evidence";
}

export function riskLevelTone(level) {
  if (level === "low" || level === "excellent" || level === "good") return "positive";
  if (level === "high") return "negative";
  return "neutral"; // medium, fair
}

export const assetDetailApi = {
  getAssetDetail: (symbol = "BTC") =>
    delay(() => {
      const detail = assetDetailData[symbol];
      if (!detail) return null;

      const meta = findAssetMeta(symbol);
      const holding = findHolding(symbol);

      return {
        symbol,
        header: {
          ...detail.header,
          logoColor: meta?.logoColor || "var(--sv2-accent)",
          subcategory: meta?.subcategory || null,
          held: !!holding,
          quantityHeld: holding?.quantity ?? null,
        },
        priceHistory: detail.priceHistory,
        forecast: detail.forecast,
        aaiPanel: detail.aaiPanel,
        riskOverview: detail.riskOverview,
        marketStats: detail.marketStats,
        signalCard: detail.signalCard,
        about: detail.about,
        relatedAssets: detail.relatedAssets || [],
        sentimentSnippet: detail.sentimentSnippet,
      };
    }),

  // Builds "Similar assets" from relatedAssets, backfilled by market cap
  // if fewer than 4 related symbols are available for this asset.
  getSimilarAssets: (symbol = "BTC", relatedAssets = []) =>
    delay(() => {
      const pool = assetsData.assets.filter((a) => a.symbol !== symbol);
      const related = relatedAssets
        .map((sym) => pool.find((a) => a.symbol === sym))
        .filter(Boolean);

      const remaining = pool
        .filter((a) => !related.includes(a))
        .sort((a, b) => b.marketCap - a.marketCap);

      const combined = [...related, ...remaining].slice(0, 4);

      return combined.map((a) => {
        const history = assetDetailData[a.symbol]?.priceHistory || [];
        return {
          symbol: a.symbol,
          name: a.name,
          logoColor: a.logoColor,
          price: a.price,
          change24h: a.change24h,
          sparkline: history.map((p) => p.price),
          aaiScore: a.aai?.score ?? null,
          signal: a.aai?.signal ?? null,
          held: !!findHolding(a.symbol),
          watching: !!a.watching,
        };
      });
    }),
};