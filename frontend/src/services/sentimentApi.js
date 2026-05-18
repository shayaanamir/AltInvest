import { asset_sentiment } from '../data/sample_data';
import { USE_MOCK, API_BASE_URL } from "../config";

export const sentimentApi = {
  getSentimentSources: async () => {
    if (USE_MOCK) {
      return new Promise((resolve) => {
        setTimeout(() => {
          let totalNews = 0;
          let totalSignals = 0;
          let count = 0;

          asset_sentiment.forEach(asset => {
            if (asset.source_breakdown) {
              totalNews += asset.source_breakdown.news_nlp || 0;
              totalSignals += asset.source_breakdown.market_signals || 0;
              count++;
            }
          });

          if (count > 0) {
            resolve({
              news: (totalNews / count) * 100,
              signals: (totalSignals / count) * 100
            });
          } else {
            resolve({ news: 0, signals: 0 });
          }
        }, 500);
      });
    }

    const res = await fetch(`${API_BASE_URL}/sentiment/sources`);
    if (!res.ok) throw new Error("Failed to fetch sentiment sources");
    return res.json();
  },

  getTopHeadlines: async () => {
    if (USE_MOCK) {
      return new Promise((resolve) => {
        setTimeout(() => {
          let allHeadlines = [];
          asset_sentiment.forEach(asset => {
            if (asset.top_headlines) {
              const withAssetId = asset.top_headlines.map(h => ({
                ...h,
                asset_id: asset.asset_id
              }));
              allHeadlines = [...allHeadlines, ...withAssetId];
            }
          });
          
          allHeadlines.sort((a, b) => a.age_hours - b.age_hours);
          resolve(allHeadlines);
        }, 500);
      });
    }

    const res = await fetch(`${API_BASE_URL}/sentiment/headlines`);
    if (!res.ok) throw new Error("Failed to fetch headlines");
    return res.json();
  },

  getGlobalSentiment: async () => {
    if (USE_MOCK) {
      return new Promise((resolve) => {
        setTimeout(() => {
          let totalScore = 0;
          let count = 0;

          asset_sentiment.forEach(asset => {
            if (typeof asset.sentiment_score === 'number') {
              totalScore += asset.sentiment_score;
              count++;
            }
          });

          resolve(count > 0 ? (totalScore / count) : 0.5);
        }, 500);
      });
    }

    const res = await fetch(`${API_BASE_URL}/sentiment/global`);
    if (!res.ok) throw new Error("Failed to fetch global sentiment");
    const data = await res.json();
    return data.score;
  }
};
