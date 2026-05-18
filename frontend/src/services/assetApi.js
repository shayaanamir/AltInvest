import { assets, assetMarketData, trendingAssets, assetPriceHistory, assetPricePredictions, aaiScores } from '../data/sample_data';
import { USE_MOCK, API_BASE_URL } from "../config";

export const assetApi = {
  getAssetHeader: async (assetId = 101) => {
    if (USE_MOCK) {
      return new Promise((resolve) => {
        setTimeout(() => {
          const asset = assets.find(a => a.id === assetId);
          const marketData = assetMarketData.find(m => m.asset_id === assetId);
          const trending = trendingAssets.find(t => t.asset_id === assetId);

          resolve({
            id: asset?.id,
            symbol: asset?.symbol || "UNK",
            name: asset?.name || "Unknown Asset",
            asset_type: asset?.asset_type || "unknown",
            price: marketData ? marketData.price : 0,
            change: trending ? trending.movement_percentage : 0,
          });
        }, 500);
      });
    }

    const res = await fetch(`${API_BASE_URL}/assets/${assetId}/header`);
    if (!res.ok) throw new Error("Failed to fetch asset header");
    return res.json();
  },

  getAssetPricePerformance: async (assetId = 101, mode = "Price", filter = "1M") => {
    if (USE_MOCK) {
      return new Promise((resolve) => {
        setTimeout(() => {
          let dataSrc = mode === "AI Prediction" ? assetPricePredictions : assetPriceHistory;
          let filtered = dataSrc.filter(d => d.asset_id === assetId);
          
          filtered.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

          resolve(filtered.map(d => ({
            date: d.timestamp,
            value: d.price
          })));
        }, 500);
      });
    }

    const res = await fetch(`${API_BASE_URL}/assets/${assetId}/performance?mode=${mode}&filter=${filter}`);
    if (!res.ok) throw new Error("Failed to fetch asset performance");
    return res.json();
  },

  getAssetIntelligence: async (assetId = 101) => {
    if (USE_MOCK) {
      return new Promise((resolve) => {
        setTimeout(() => {
          const data = aaiScores.find(s => s.asset_id === assetId);
          resolve(data || { score: 0, confidence: 50 });
        }, 500);
      });
    }

    const res = await fetch(`${API_BASE_URL}/assets/${assetId}/intelligence`);
    if (!res.ok) throw new Error("Failed to fetch asset intelligence");
    return res.json();
  }
};
