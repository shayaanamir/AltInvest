import { apiFetch } from "./apiClient";

// Backend global_sentiment is -1..1; the dashboard gauge reads 0..100.
const sentimentTo100 = (s) => Math.round(((s ?? 0) + 1) * 50);

export const dashboardApi = {
  getCurrentUser: async () => {
    const p = await apiFetch("/profile");
    return { name: p.name, initials: p.avatar_initials, color: p.avatar_color };
  },

  getNotificationCount: async () => {
    const items = await apiFetch("/notifications?limit=20");
    return items.filter((n) => !n.read).length;
  },

  getMarketStats: async () => {
    const s = await apiFetch("/dashboard/stats");
    return {
      totalPortfolioValue: s.portfolio_value_usd,
      holdingsCount: s.holdings_count,
      totalVolume24h: s.volume_24h_usd,
      assetsCount: s.assets_count,
      collectionsCount: s.collections_count,
      globalSentiment: sentimentTo100(s.global_sentiment),
      cryptoScoreCount: s.crypto_score_count,
      nftScoreCount: s.nft_score_count,
      marketMood: s.global_sentiment_label.toLowerCase(),
      marketMoodConfidence: s.market_mood_confidence == null ? null : Math.round(s.market_mood_confidence),
    };
  },

  // [{date, value}] — empty when portfolio_snapshots has nothing for the range.
  getPerformanceHistory: async (filter = "1M") => {
    const res = await apiFetch(`/dashboard/performance?filter=${filter}`);
    return res.points.map((p) => ({ date: p.timestamp, value: p.value }));
  },

  getMarketInsights: async () => {
    const rows = await apiFetch("/dashboard/insights");
    return rows.map((r, i) => ({
      id: `${r.published_at}-${i}`,
      source: r.source,
      title: r.title,
      summary: r.summary,
      impact: r.impact,
      publishedAt: r.published_at,
      relatedAssetSymbol: r.related_asset_symbol,
      relatedNftSlug: r.related_nft_slug,
    }));
  },

  getTrendingAssets: async () => {
    const rows = await apiFetch("/dashboard/trending");
    return rows.map((r) => ({
      symbol: r.symbol,
      name: r.name,
      logoColor: r.logo_color,
      price: r.price,
      change24h: r.change_24h,
      sparkline: r.sparkline,
      aai: { score: r.aai_score, signal: r.signal },
    }));
  },

  getTrendingCollections: async () => {
    const rows = await apiFetch("/dashboard/trending-collections");
    return rows.map((r) => ({
      slug: r.slug,
      name: r.name,
      symbol: r.symbol,
      bannerColor: r.banner_color,
      floorEth: r.floor_eth,
      floorUsd: r.floor_usd,
      change24h: r.change_24h,
      aai: { score: r.aai_score },
    }));
  },
};
