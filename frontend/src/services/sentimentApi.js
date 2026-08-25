import { asset_sentiment } from '../data/sample_data';
// import { USE_MOCK, API_BASE_URL } from "../config";

import {API_BASE_URL } from "../config";

const USE_MOCK = false;


/**
 * sentimentApi
 *
 * Fetches sentiment data from the backend (GET /sentiment) which proxies to
 * the real sentiment engine.  Falls back to local sample data when USE_MOCK=true.
 *
 * Real engine response shape (array):
 * [
 *   {
 *     asset_id:               "btc",
 *     sentiment_score:        0.72,    // 0-1
 *     confidence:             0.87,
 *     confidence_label:       "high",
 *     signal_strength:        "strong",
 *     trend:                  "improving",
 *     last_updated:           "2026-05-18T18:00:00+00:00",
 *     article_count:          45,
 *     source_count:           8,
 *     source_breakdown:       { news_nlp: 0.75, market_signals: 0.68 },
 *     sentiment_distribution: { Positive: 32, Negative: 8, neutral: 5 },
 *     top_headlines:          [{ title, score, source, age_hours, link }],
 *     market_signals:         { price_change_24h, volume_change_24h, is_trending, btc_dominance },
 *     articles_by_source:     { CoinDesk: 12, ... },
 *   },
 *   ...
 * ]
 */
export const sentimentApi = {

  /** Fetch all-asset sentiment and reshape for the dashboard components. */
  getSentimentData: async () => {
    let data;

    if (USE_MOCK) {
      data = await new Promise((resolve) => {
        setTimeout(() => resolve(asset_sentiment), 500);
      });
    } else {
      const res = await fetch(`${API_BASE_URL}/sentiment`);
      if (!res.ok) throw new Error(`Failed to fetch sentiment data (${res.status})`);
      data = await res.json();
    }

    // Normalise: real engine returns a plain array; mock may return the same.
    const list = Array.isArray(data) ? data : (data.assets ?? []);

    let totalScore   = 0, scoreCount   = 0;
    let totalNews    = 0, totalSignals = 0, sourcesCount = 0;
    let headlines    = [];

    list.forEach(asset => {
      // ── Global Sentiment ─────────────────────────────────────────────────
      if (typeof asset.sentiment_score === 'number') {
        totalScore += asset.sentiment_score;
        scoreCount++;
      }

      // ── Source Breakdown ─────────────────────────────────────────────────
      if (asset.source_breakdown) {
        totalNews    += asset.source_breakdown.news_nlp       ?? 0;
        totalSignals += asset.source_breakdown.market_signals ?? 0;
        sourcesCount++;
      }

      // ── Headlines ────────────────────────────────────────────────────────
      if (Array.isArray(asset.top_headlines)) {
        const tagged = asset.top_headlines.map(h => ({
          ...h,
          asset_id: asset.asset_id ?? asset.asset ?? "?",
        }));
        headlines = [...headlines, ...tagged];
      }
    });

    // Sort headlines: most recent first (smallest age_hours)
    headlines.sort((a, b) => (a.age_hours ?? 0) - (b.age_hours ?? 0));

    return {
      globalScore: scoreCount > 0 ? (totalScore / scoreCount) : 0.5,
      sources: sourcesCount > 0
        ? {
            news:    (totalNews    / sourcesCount) * 100,
            signals: (totalSignals / sourcesCount) * 100,
          }
        : { news: 0, signals: 0 },
      headlines,
      rawData: list,
    };
  },

  /** Fetch historical sentiment scores for a single asset (for charting). */
  getSentimentHistory: async (assetId = 'btc', days = 30) => {
    if (USE_MOCK) {
      // Return a flat array of { date, score } from sample data (best-effort)
      return [];
    }
    const res = await fetch(`${API_BASE_URL}/sentiment/${assetId}/history?days=${days}`);
    if (!res.ok) throw new Error(`Failed to fetch sentiment history (${res.status})`);
    const json = await res.json();
    // json = { asset_id, days, count, history: [...] }
    return (json.history ?? []).map(h => ({
      date:  h.last_updated ?? h.timestamp ?? '',
      score: h.sentiment_score ?? 0.5,
    }));
  },

  /** Force a pipeline re-run for an asset. */
  refreshSentiment: async (assetId = 'btc') => {
    const res = await fetch(`${API_BASE_URL}/sentiment/${assetId}/refresh`, { method: 'POST' });
    if (!res.ok) throw new Error(`Refresh failed (${res.status})`);
    return res.json();
  },
};
