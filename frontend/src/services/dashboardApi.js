import { 
  portfolioHoldings, 
  assetMarketData, 
  assetSentiment,
  portfolioSnapshots,
  assetPriceHistory,
  marketInsights
} from '../data/sample_data';
import { USE_MOCK, API_BASE_URL } from "../config";

export const dashboardApi = {
  getStats: async () => {
    if (USE_MOCK) {
      return new Promise((resolve) => {
        setTimeout(() => {
          let totalPortfolioValue = 0;
          portfolioHoldings.forEach(holding => {
            const marketData = assetMarketData.find(m => m.asset_id === holding.asset_id);
            if (marketData) {
              totalPortfolioValue += holding.quantity * marketData.price;
            }
          });

          let totalVolume24h = 0;
          assetMarketData.forEach(data => {
            totalVolume24h += data.volume_24h;
          });

          let totalSentiment = 0;
          let sentimentCount = 0;
          assetSentiment.forEach(s => {
            totalSentiment += s.fear_greed_index; 
            sentimentCount++;
          });
          const avgSentiment = sentimentCount > 0 ? Math.round(totalSentiment / sentimentCount) : 0;

          let mood = "neutral";
          if (avgSentiment >= 60) mood = "bullish";
          else if (avgSentiment <= 40) mood = "bearish";

          const snapshots = [...portfolioSnapshots].sort((a, b) => new Date(b.snapshot_date) - new Date(a.snapshot_date));
          let portfolioChangePct = 0;
          let portfolioPositive = true;
          if (snapshots.length >= 2) {
            const current = snapshots[0].total_value;
            const previous = snapshots[1].total_value;
            portfolioChangePct = ((current - previous) / previous) * 100;
            portfolioPositive = portfolioChangePct >= 0;
          }

          let volToday = 0;
          let volYesterday = 0;
          assetPriceHistory.forEach(h => {
            if (h.timestamp.startsWith("2026-05-18")) volToday += h.volume;
            if (h.timestamp.startsWith("2026-05-17")) volYesterday += h.volume;
          });
          let volumeChangePct = 0;
          let volumePositive = true;
          if (volYesterday > 0) {
             volumeChangePct = ((volToday - volYesterday) / volYesterday) * 100;
             volumePositive = volumeChangePct >= 0;
          }

          resolve({
            totalPortfolioValue,
            totalVolume24h,
            globalSentiment: avgSentiment,
            marketMood: mood,
            portfolioChange: Math.abs(portfolioChangePct).toFixed(2) + "%",
            portfolioPositive,
            volumeChange: Math.abs(volumeChangePct).toFixed(2) + "%",
            volumePositive,
            sentimentChange: "4.1%", 
            sentimentPositive: true
          });
        }, 500); 
      });
    }

    const res = await fetch(`${API_BASE_URL}/dashboard/stats`);
    if (!res.ok) throw new Error("Failed to fetch dashboard stats");
    return res.json();
  },

  getPerformanceData: async (filter = "1M") => {
    if (USE_MOCK) {
      return new Promise((resolve) => {
        setTimeout(() => {
          const sorted = [...portfolioSnapshots].sort((a, b) => new Date(a.snapshot_date) - new Date(b.snapshot_date));
          resolve(sorted.map(s => ({
            date: s.snapshot_date,
            value: s.total_value
          })));
        }, 500);
      });
    }

    const res = await fetch(`${API_BASE_URL}/dashboard/performance?filter=${filter}`);
    if (!res.ok) throw new Error("Failed to fetch performance data");
    return res.json();
  },

  getMarketInsights: async () => {
    if (USE_MOCK) {
      return new Promise((resolve) => {
        setTimeout(() => {
          resolve(marketInsights);
        }, 500);
      });
    }

    const res = await fetch(`${API_BASE_URL}/dashboard/insights`);
    if (!res.ok) throw new Error("Failed to fetch market insights");
    return res.json();
  }
};
