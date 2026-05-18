import { asset_sentiment } from '../data/sample_data';
import { USE_MOCK, API_BASE_URL } from "../config";

export const sentimentApi = {
  getSentimentData: async () => {
    let data;
    
    if (USE_MOCK) {
      data = await new Promise((resolve) => {
        setTimeout(() => {
          resolve(asset_sentiment);
        }, 500);
      });
    } else {
      const res = await fetch(`${API_BASE_URL}/sentiment`);
      if (!res.ok) throw new Error("Failed to fetch sentiment data");
      data = await res.json();
    }

    // Process the entire JSON into the pieces needed by the frontend components
    let totalScore = 0;
    let scoreCount = 0;
    
    let totalNews = 0;
    let totalSignals = 0;
    let sourcesCount = 0;
    
    let headlines = [];

    data.forEach(asset => {
      // Global Sentiment
      if (typeof asset.sentiment_score === 'number') {
        totalScore += asset.sentiment_score;
        scoreCount++;
      }
      
      // Sources
      if (asset.source_breakdown) {
        totalNews += asset.source_breakdown.news_nlp || 0;
        totalSignals += asset.source_breakdown.market_signals || 0;
        sourcesCount++;
      }
      
      // Headlines
      if (asset.top_headlines) {
        const withAssetId = asset.top_headlines.map(h => ({
          ...h,
          asset_id: asset.asset_id
        }));
        headlines = [...headlines, ...withAssetId];
      }
    });

    headlines.sort((a, b) => a.age_hours - b.age_hours);

    return {
      globalScore: scoreCount > 0 ? (totalScore / scoreCount) : 0.5,
      sources: sourcesCount > 0 ? {
        news: (totalNews / sourcesCount) * 100,
        signals: (totalSignals / sourcesCount) * 100
      } : { news: 0, signals: 0 },
      headlines: headlines,
      rawData: data // Just in case
    };
  }
};
