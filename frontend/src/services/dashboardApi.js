import { 
  portfolioHoldings, 
  assetMarketData, 
  assetSentiment 
} from '../data/sample_data';
import { USE_MOCK, API_BASE_URL } from "../config";

export const dashboardApi = {
  getStats: async () => {
    if (USE_MOCK) {
      return new Promise((resolve) => {
        setTimeout(() => {
          // 1. Total Portfolio Value
          let totalPortfolioValue = 0;
          portfolioHoldings.forEach(holding => {
            const marketData = assetMarketData.find(m => m.asset_id === holding.asset_id);
            if (marketData) {
              totalPortfolioValue += holding.quantity * marketData.price;
            }
          });

          // 2. 24h Volume (Alt)
          let totalVolume24h = 0;
          assetMarketData.forEach(data => {
            totalVolume24h += data.volume_24h;
          });

          // 3. Global AAI Sentiment
          let totalSentiment = 0;
          let sentimentCount = 0;
          assetSentiment.forEach(s => {
            // Using positive_score or fear_greed_index as proxy for sentiment score
            totalSentiment += s.fear_greed_index; 
            sentimentCount++;
          });
          const avgSentiment = sentimentCount > 0 ? Math.round(totalSentiment / sentimentCount) : 0;

          // 4. Market Mood
          let mood = "neutral";
          if (avgSentiment >= 60) mood = "bullish";
          else if (avgSentiment <= 40) mood = "bearish";

          resolve({
            totalPortfolioValue,
            totalVolume24h,
            globalSentiment: avgSentiment,
            marketMood: mood,
            // mock percent changes
            portfolioChange: "▲ 2.65%",
            portfolioPositive: true,
            volumeChange: "▼ 1.2%",
            volumePositive: false,
            sentimentChange: "▲ 4.1%",
            sentimentPositive: true
          });
        }, 500); // simulated network delay
      });
    }

    // --- REAL IMPLEMENTATION ---
    const res = await fetch(`${API_BASE_URL}/dashboard/stats`);
    if (!res.ok) throw new Error("Failed to fetch dashboard stats");
    return res.json();
  }
};
