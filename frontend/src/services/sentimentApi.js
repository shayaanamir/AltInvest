import { asset_sentiment, newsArticles } from "../data/sample_data";
import { USE_MOCK, API_BASE_URL } from "../config";
import { confidenceLabelFromValue, getEvidencePhrase as evidencePhrase, bandByThreshold } from "../utils/scoring";

/* ============================================================
   Static metadata the sentiment engine doesn't return yet
   (category / subcategory / price / portfolio flag). Filled in
   only where the backend has no equivalent field.
   ============================================================ */
const ASSET_META = {
  btc:  { symbol: "BTC",  name: "Bitcoin",            category: "crypto", subcategory: "Layer 1",             held: false },
  eth:  { symbol: "ETH",  name: "Ethereum",           category: "crypto", subcategory: "Layer 1",             held: true  },
  sol:  { symbol: "SOL",  name: "Solana",             category: "crypto", subcategory: "Layer 1",             held: true  },
  bayc: { symbol: "BAYC", name: "Bored Ape YC",       category: "nft",    subcategory: "Blue-chip",           held: false },
  link: { symbol: "LINK", name: "Chainlink",          category: "crypto", subcategory: "Infrastructure",      held: false },
  doge: { symbol: "DOGE", name: "Dogecoin",           category: "crypto", subcategory: "Meme/Community",      held: false },
  arb:  { symbol: "ARB",  name: "Arbitrum",           category: "crypto", subcategory: "Layer 2",             held: false },
  dai:  { symbol: "DAI",  name: "Dai",                category: "crypto", subcategory: "Stablecoin-adjacent", held: true  },
  uni:  { symbol: "UNI",  name: "Uniswap",            category: "crypto", subcategory: "DeFi",                held: false },
  base: { symbol: "BASE", name: "Base Ecosystem Index", category: "crypto", subcategory: "Layer 2",           held: false },
};

// Filler rows for assets the sentiment engine doesn't cover in this phase.
const FILLER_ROWS = [
  { assetId: "link", changePct: 1.10 },
  { assetId: "doge", changePct: 11.62 },
  { assetId: "arb",  changePct: 3.87 },
  { assetId: "dai",  changePct: 0.0 },
  { assetId: "uni",  changePct: -4.06 },
  { assetId: "base", changePct: 0.42 },
];

const THEMES = [
  { label: "Restaking yields", direction: "up" },
  { label: "Spot ETF inflows", direction: "up" },
  { label: "L2 fee compression", direction: "up" },
  { label: "Regulatory hearings", direction: "down" },
  { label: "Depeg chatter", direction: "down" },
];

const NFT_CHATTER_FILLER = [
  { title: "Blue-chip floor prices stabilize after a choppy week", score: 0.4, source: "NFTNow", age_hours: 2.1, link: "#" },
  { title: "Gaming collections see renewed mint activity", score: 0.6, source: "Decrypt", age_hours: 5.4, link: "#" },
  { title: "Royalty enforcement debate resurfaces across marketplaces", score: -0.5, source: "CoinTelegraph", age_hours: 9.2, link: "#" },
];

export const WATCHLIST = ["btc", "eth", "sol"];

// Mirrors backend/routes/sentiment.py::_ACTIVE_ASSETS — keep these two in
// sync whenever backend coverage changes.
export const ACTIVE_ASSETS = ["btc", "eth", "sol"];

/* ---------------- helpers ---------------- */

const FETCH_TIMEOUT_MS = 18000;         // GET requests (list/history)
const REFRESH_TIMEOUT_MS = 30000;       // POST /refresh — triggers a full pipeline run

async function fetchWithTimeout(url, options = {}, timeoutMs = FETCH_TIMEOUT_MS) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timeoutId);
  }
}

function describeFetchError(e) {
  return e.name === "AbortError" ? "request timed out" : e.message;
}

function normaliseRecord(raw) {
  return {
    assetId: (raw.asset_id || raw.asset || "").toLowerCase(),
    sentimentScore: raw.sentiment_score ?? 0,
    confidence: raw.confidence ?? 0.5,
    confidenceLabel: raw.confidence_label ?? "medium",
    trend: raw.trend ?? "stable",
    articleCount: raw.article_count ?? raw.post_count ?? 0,
    sourceCount: raw.source_count ?? 0,
    sourceBreakdown: raw.source_breakdown ?? { news_nlp: 0.5, market_signals: 0.5 },
    distribution: raw.sentiment_distribution ?? { positive: 0, negative: 0, neutral: 0 },
    topHeadlines: raw.top_headlines ?? [],
    marketSignals: raw.market_signals ?? {},
    articlesBySource: raw.articles_by_source ?? {},
    lastUpdated: raw.last_updated ?? raw.timestamp ?? new Date().toISOString(),
  };
}

async function fetchAllSentimentRaw() {
  if (USE_MOCK) return asset_sentiment;
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/sentiment`);
    if (!res.ok) throw new Error(`status ${res.status}`);
    const data = await res.json();
    if (Array.isArray(data) && data.length) {
      const seen = new Set();
      const unique = [];
      for (const item of data) {
        const id = (item.asset_id || item.asset || "").toLowerCase();
        if (id && !seen.has(id)) {
          seen.add(id);
          unique.push(item);
        }
      }
      return unique;
    }
    return asset_sentiment;
  } catch (e) {
    console.warn(`sentimentApi: backend unavailable, using sample data (${describeFetchError(e)})`);
    return asset_sentiment;
  }
}

async function fetchHistoryRaw(assetId, days) {
  if (!USE_MOCK) {
    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/sentiment/${assetId}/history?days=${days}`);
      if (res.ok) {
        const json = await res.json();
        if (json.history?.length >= 2) return json.history;
      }
    } catch (e) {
      console.warn(`sentimentApi: history fetch failed, using synthetic series (${describeFetchError(e)})`);
    }
  }
  return null;
}

function synthesizeWave(len, base, amp) {
  return Array.from({ length: len }, (_, i) => {
    const t = (i / len) * Math.PI * 2 * 3.2;
    return Math.round(base + amp * Math.sin(t) + amp * 0.3 * Math.sin(t * 2.1 + 1));
  });
}

function moodLabel(score, kind) {
  if (kind === "nft") {
    if (score >= 10) return "Heating Up";
    if (score <= -10) return "Cooling";
    return "Neutral";
  }
  if (kind === "realestate" || kind === "real_estate") {
    if (score >= 10) return "Appreciating";
    if (score <= -10) return "Declining";
    return "Neutral";
  }
  if (score >= 10) return "Bullish";
  if (score <= -10) return "Bearish";
  return "Neutral";
}

const QUALITATIVE_BANDS = [
  { min: 70, label: "Strongly Positive" },
  { min: 58, label: "Positive" },
  { min: 45, label: "Mixed" },
  { min: 35, label: "Neutral" },
  { min: -Infinity, label: "Negative" },
];

export function qualitativeLabel(score) {
  return bandByThreshold(score, QUALITATIVE_BANDS, null)?.label ?? null;
}

export { confidenceLabelFromValue, evidencePhrase };
export { relativeTime } from "../utils/dateTime";

/* ---------------- public API ---------------- */

export const sentimentApi = {
  ASSET_META,

  /** Two mood-gauge summaries for the hub header. */
  getMoodOverview: async () => {
    const raw = await fetchAllSentimentRaw();
    const records = raw.map(normaliseRecord).map((r) => ({ ...r, meta: ASSET_META[r.assetId] || null }));

    const cryptoRecords = records.filter((r) => (r.meta?.category ?? "crypto") === "crypto");
    const nftRecords = records.filter((r) => r.meta?.category === "nft");
    const realEstateRecords = records.filter((r) => r.meta?.category === "realestate" || r.meta?.category === "real_estate");

    const buildSummary = (list) => {
      if (!list.length) return null;
      const avgScore = Math.round(list.reduce((s, r) => s + r.sentimentScore * 100, 0) / list.length);
      const avgConfidence = list.reduce((s, r) => s + r.confidence, 0) / list.length;
      return { avgScore, confidence: avgConfidence, count: list.length };
    };

    const cryptoSummary = buildSummary(cryptoRecords) ?? { avgScore: 19, confidence: 0.55, count: 8 };
    const nftSummary = buildSummary(nftRecords);
    const realEstateSummary = buildSummary(realEstateRecords);

    return {
      crypto: {
        avgScore: cryptoSummary.avgScore,
        label: moodLabel(cryptoSummary.avgScore, "crypto"),
        confidenceLabel: confidenceLabelFromValue(cryptoSummary.confidence),
        assetCount: cryptoSummary.count,
        excludedCount: 0,
      },
      nft: nftSummary
        ? {
            avgScore: nftSummary.avgScore,
            label: moodLabel(nftSummary.avgScore, "nft"),
            confidenceLabel: confidenceLabelFromValue(nftSummary.confidence),
            assetCount: Math.max(nftSummary.count, 6),
            excludedCount: 1,
          }
        : { avgScore: 17, label: "Neutral", confidenceLabel: "medium", assetCount: 6, excludedCount: 1 },
      realEstate: realEstateSummary
        ? {
            avgScore: realEstateSummary.avgScore,
            label: moodLabel(realEstateSummary.avgScore, "realestate"),
            confidenceLabel: confidenceLabelFromValue(realEstateSummary.confidence),
            propertyCount: realEstateSummary.count,
            excludedCount: 1,
          }
        : { avgScore: 12, label: "Neutral", confidenceLabel: "low", propertyCount: 4, excludedCount: 1 },
    };
  },

  getMoodTrend: async (scope = "crypto", days = 30) => {
    if (scope === "both") {
      const crypto = await sentimentApi.getMoodTrend("crypto", days);
      const nft = await sentimentApi.getMoodTrend("nft", days);
      const realEstate = await sentimentApi.getMoodTrend("realEstate", days);
      return { crypto, nft, realEstate };
    }

    const n = days === 7 ? 40 : days === 90 ? 120 : 80;

    const history = await fetchHistoryRaw("btc", days);
    const hasHistory = history && history.length >= 2;

    if (scope === "crypto") {
      if (hasHistory) {
        return [...history].reverse().map((h) => ({
          date: h.last_updated || h.timestamp,
          value: Math.round(((h.sentiment_score ?? 0) + 1) * 50),
        }));
      }
      return synthesizeWave(n, 60, 14).map((v) => ({ date: null, value: v }));
    }

    if (scope === "nft") {
      if (hasHistory) {
        const length = history.length;
        const nftVals = synthesizeWave(length, 55, 8);
        return [...history].reverse().map((h, i) => ({
          date: h.last_updated || h.timestamp,
          value: nftVals[i],
        }));
      }
      return synthesizeWave(n, 55, 10).map((v) => ({ date: null, value: v }));
    }

    if (scope === "realEstate" || scope === "realestate") {
      if (hasHistory) {
        const length = history.length;
        const reVals = synthesizeWave(length, 56, 6);
        return [...history].reverse().map((h, i) => ({
          date: h.last_updated || h.timestamp,
          value: reVals[i],
        }));
      }
      return synthesizeWave(n, 56, 6).map((v) => ({ date: null, value: v }));
    }

    return synthesizeWave(n, 58, 12).map((v) => ({ date: null, value: v }));
  },

  /** Ranked asset list ("What stands out"). category: 'crypto' | 'nft' | 'all' */
  getAssetList: async (category = "crypto") => {
    const raw = await fetchAllSentimentRaw();
    const records = raw.map(normaliseRecord);

    const realRows = records
      .map((r) => {
        const meta = ASSET_META[r.assetId];
        if (!meta) return null;
        const score = Math.round((r.sentimentScore + 1) * 50);
        return {
          assetId: r.assetId,
          name: meta.name,
          symbol: meta.symbol,
          category: meta.category,
          subcategory: meta.subcategory,
          held: meta.held,
          score,
          readLabel: `${qualitativeLabel(score)}, ${evidencePhrase(r.confidenceLabel)}`,
          changePct: r.marketSignals?.price_change_24h ?? 0,
        };
      })
      .filter(Boolean);

    // Consistently unscored — no fake numbers, matching how BASE already
    // rendered before this fix.
    const fillerRows = FILLER_ROWS.map((f) => {
      const meta = ASSET_META[f.assetId];
      return {
        assetId: f.assetId,
        name: meta.name,
        symbol: meta.symbol,
        category: meta.category,
        subcategory: meta.subcategory,
        held: meta.held,
        score: null,
        readLabel: "Not covered yet",
        changePct: f.changePct,
      };
    });

    const covered = new Set(realRows.map((r) => r.assetId));
    const all = [...realRows, ...fillerRows.filter((f) => !covered.has(f.assetId))];

    const filtered = category === "all" ? all : all.filter((r) => r.category === category);

    return filtered.sort((a, b) => {
      if (a.score == null) return 1;
      if (b.score == null) return -1;
      return b.score - a.score;
    });
  },

  getThemes: async () => THEMES,

  getWhatWereReading: async (tab = "news") => {
    if (tab === "nft") return NFT_CHATTER_FILLER;
    const raw = await fetchAllSentimentRaw();
    const records = raw.map(normaliseRecord).filter((r) => ASSET_META[r.assetId]?.category === "crypto");
    let headlines = records.flatMap((r) => r.topHeadlines.map((h) => ({ ...h, assetId: r.assetId })));
    if (!headlines.length) {
      headlines = newsArticles.map((a) => ({
        title: a.title, score: 0.2, source: a.source, age_hours: 3, link: a.url, assetId: "eth",
      }));
    }
    return headlines.sort((a, b) => (a.age_hours ?? 0) - (b.age_hours ?? 0));
  },

  /** Full detail bundle for the asset drill-down view. */
  getAssetDetail: async (assetId) => {
    const raw = await fetchAllSentimentRaw();
    const records = raw.map(normaliseRecord);
    const record = records.find((r) => r.assetId === assetId);
    const meta = ASSET_META[assetId] || { symbol: assetId.toUpperCase(), name: assetId.toUpperCase(), category: "crypto", subcategory: "—", held: false };
    const filler = FILLER_ROWS.find((f) => f.assetId === assetId);

    const score = record ? Math.round((record.sentimentScore + 1) * 50) : filler?.score ?? 50;
    const sentimentScore = record ? record.sentimentScore : (filler?.score != null ? (filler.score / 50) - 1 : 0.0);
    const confidence = record ? record.confidence : 0.5;
    const confidenceLabel = record ? record.confidenceLabel : "medium";
    const label = qualitativeLabel(score) ?? "Neutral";
    const headlines = record?.topHeadlines?.length
      ? record.topHeadlines
      : [
          { title: `${meta.name} sees steady coverage across major outlets`, score: 0.3, source: "CoinDesk", age_hours: 4, link: "#" },
          { title: `Analysts weigh in on ${meta.name}'s near-term trajectory`, score: -0.1, source: "Decrypt", age_hours: 9, link: "#" },
        ];

    const tone = score >= 70 ? "broadly constructive" : score >= 55 ? "modestly constructive" : score >= 45 ? "mixed" : score >= 30 ? "cautious" : "broadly negative";
    const topics = headlines.slice(0, 2).map((h) => h.title.split(" ").slice(0, 5).join(" ").toLowerCase());
    const narrative = `Coverage is ${tone} — ${topics.join(" and ")} dominate the narrative, with ${score >= 55 ? "little contradicting commentary" : "some pushback in the comments"}.`;

    const distribution = record?.distribution ?? { positive: 63, neutral: 26, negative: 11 };
    const distTotal = Math.max(1, distribution.positive + distribution.neutral + distribution.negative);

    const drivingFactors = headlines.slice(0, 3).map((h) => ({
      direction: h.score >= 0 ? "up" : "down",
      title: h.title,
      description: `${h.source} flagged this ${Math.round(h.age_hours)}h ago.`,
    }));

    const sourceBreakdown = record?.sourceBreakdown ?? { news_nlp: 0.64, market_signals: 0.36 };
    const articlesBySource = record?.articlesBySource ?? { CoinDesk: 2, Decrypt: 1, "The Block": 1 };

    return {
      assetId,
      symbol: meta.symbol,
      name: meta.name,
      category: meta.category,
      subcategory: meta.subcategory,
      held: meta.held,
      price: meta.price ?? 3418.02,
      priceChangePct: record?.marketSignals?.price_change_24h ?? filler?.changePct ?? 0,
      score,
      sentimentScore,
      label,
      confidencePct: Math.round(confidence * 100),
      confidenceLabel,
      narrative,
      trend: record?.trend ?? "stable",
      distribution: {
        positive: Math.round((distribution.positive / distTotal) * 100),
        neutral: Math.round((distribution.neutral / distTotal) * 100),
        negative: Math.round((distribution.negative / distTotal) * 100),
      },
      articleCount: record?.articleCount ?? headlines.length,
      drivingFactors,
      headlines,
      sourceBreakdown: {
        newsPct: Math.round((sourceBreakdown.news_nlp ?? 0.5) * 100),
        marketPct: Math.round((sourceBreakdown.market_signals ?? 0.5) * 100),
      },
      articlesBySource,
      marketSignals: {
        priceChange24h: record?.marketSignals?.price_change_24h ?? filler?.changePct ?? 0,
        volumeChange24h: record?.marketSignals?.volume_change_24h ?? 18.6,
        isTrending: record?.marketSignals?.is_trending ?? true,
        btcDominance: record?.marketSignals?.btc_dominance ?? 54.1,
      },
      lastUpdated: record?.lastUpdated ?? new Date().toISOString(),
    };
  },

  getAssetOverTime: async (assetId, days = 30) => {
    const history = await fetchHistoryRaw(assetId, days);
    if (history?.length >= 2) {
      return [...history].reverse().map((h) => ({
        date: h.last_updated || h.timestamp,
        value: Math.round(((h.sentiment_score ?? 0) + 1) * 50),
      }));
    }
    const n = days === 24 || days === "24h" ? 24 : days === 7 ? 40 : days === 90 ? 120 : 80;
    return synthesizeWave(n, 58, 10).map((v) => ({ date: null, value: v }));
  },

  refreshAsset: async (assetId) => {
    if (USE_MOCK) return sentimentApi.getAssetDetail(assetId);
    try {
      await fetchWithTimeout(`${API_BASE_URL}/sentiment/${assetId}/refresh`, { method: "POST" }, REFRESH_TIMEOUT_MS);
    } catch (e) {
      console.warn(`sentimentApi: refresh failed for ${assetId} (${describeFetchError(e)})`);
    }
    return sentimentApi.getAssetDetail(assetId);
  },

  /** Refreshes every actively-covered asset — used by the Hub's "Refresh Pipeline" button. */
  refreshAllActive: async () => {
    if (USE_MOCK) return;
    await Promise.all(
      ACTIVE_ASSETS.map((assetId) =>
        fetchWithTimeout(`${API_BASE_URL}/sentiment/${assetId}/refresh`, { method: "POST" }, REFRESH_TIMEOUT_MS).catch(
          (e) => console.warn(`sentimentApi: refresh failed for ${assetId} (${describeFetchError(e)})`)
        )
      )
    );
  },

  getSwitchableAssets: async () => {
    const rows = await sentimentApi.getAssetList("all");
    return rows.filter((r) => r.score != null).map((r) => ({ id: r.assetId, name: r.name, symbol: r.symbol }));
  },
};