import dashboardData from "../data/sample_data/dashboard.json";
import assetsData from "../data/sample_data/assets.json";
import portfolioData from "../data/sample_data/portfolio.json";
import nftCollectionsData from "../data/sample_data/nftCollections.json";
import userData from "../data/sample_data/user.json";
import notificationsData from "../data/sample_data/notifications.json";

const SIM_DELAY = 400;

function delay(fn) {
  return new Promise((resolve) => setTimeout(() => resolve(fn()), SIM_DELAY));
}

export const dashboardApi = {
  getCurrentUser: () =>
    delay(() => ({
      name: userData.name,
      initials: userData.avatarInitials,
      color: userData.avatarColor,
    })),

  getNotificationCount: () => delay(() => notificationsData.unreadCount ?? 0),

  getMarketStats: () =>
    delay(() => {
      const { stats } = dashboardData;
      const holdingsCount =
        (portfolioData.cryptoHoldings?.length || 0) + (portfolioData.nftHoldings?.length || 0);
      const assetsCount = assetsData.assets.length;
      const collectionsCount = nftCollectionsData.collections.length;
      const cryptoScores = assetsData.assets
        .map((a) => a.aai?.score)
        .filter((v) => typeof v === "number");
      const nftScores = nftCollectionsData.collections
        .map((c) => c.aai?.score)
        .filter((v) => typeof v === "number");

      return {
        totalPortfolioValue: stats.totalPortfolioValue,
        holdingsCount,
        totalVolume24h: stats.totalVolume24h,
        assetsCount,
        collectionsCount,
        globalSentiment: Math.round(stats.globalSentiment),
        cryptoScoreCount: cryptoScores.length,
        nftScoreCount: nftScores.length,
        marketMood: stats.marketMood,
        marketMoodConfidence: stats.marketMoodConfidence,
      };
    }),

  getPerformanceHistory: (filter = "1M") =>
    delay(() => dashboardData.performanceHistory[filter] || []),

  getMarketInsights: () => delay(() => dashboardData.insights),

  getTrendingAssets: () =>
    delay(() =>
      dashboardData.trendingAssets
        .map((t) => {
          const asset = assetsData.assets.find((a) => a.symbol === t.symbol);
          return asset ? { ...asset, sparkline: t.sparkline } : null;
        })
        .filter(Boolean)
    ),

  getTrendingCollections: () =>
    delay(() =>
      dashboardData.trendingCollections
        .map((t) => {
          const collection = nftCollectionsData.collections.find((c) => c.slug === t.slug);
          return collection ? { ...collection, sparkline: t.sparkline } : null;
        })
        .filter(Boolean)
    ),
};