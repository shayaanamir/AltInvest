import { API_BASE_URL } from "../config";
import { ApiError, kindFromStatus } from "../errors/errorCatalog";
import { reportApiReachable } from "../errors/connectionStatus";
import { confidenceLabelFromValue, getEvidencePhrase as evidencePhrase, bandByThreshold } from "../utils/scoring";
import { fetchUniverse } from "./assetRepository";
import { watchlistApi } from "./watchlistApi";

/*
 * Sentiment screens. Every figure here comes from the API:
 *   GET /sentiment              latest reading per covered asset (the sentiment engine's output)
 *   GET /sentiment/{id}/history readings over time
 *   GET /sentiment/mood-trend   the average of all assets over time
 *   GET /sentiment/themes       recurring themes
 *   GET /discover               names, categories, prices, 24h change and the user's held flags
 * Where there is no data (no NFT or real-estate sentiment source, no history yet) the result is empty
 * or null so the screen can say so; nothing is filled in.
 */

/* ---------------- transport ---------------- */

const FETCH_TIMEOUT_MS = 18000;         // GET requests
const REFRESH_TIMEOUT_MS = 30000;       // POST /refresh — triggers a full pipeline run

async function fetchWithTimeout(url, options = {}, timeoutMs = FETCH_TIMEOUT_MS) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    reportApiReachable(true);
    return res;
  } catch (e) {
    reportApiReachable(false);
    throw e;
  } finally {
    clearTimeout(timeoutId);
  }
}

function describeFetchError(e) {
  return e.name === "AbortError" ? "request timed out" : e.message;
}

async function failFrom(res, what) {
  const body = await res.json().catch(() => ({}));
  return new ApiError(`${what} failed: ${res.status}`, {
    status: res.status,
    kind: kindFromStatus(res.status),
    detail: typeof body.detail === "string" ? body.detail : null,
  });
}

/** GET a JSON endpoint; throws an ApiError the UI can show with a Retry button. */
async function getJson(path, what = "Request") {
  let res;
  try {
    res = await fetchWithTimeout(`${API_BASE_URL}${path}`);
  } catch (e) {
    throw new ApiError(describeFetchError(e), { kind: e.name === "AbortError" ? "timeout" : "network" });
  }
  if (!res.ok) throw await failFrom(res, what);
  return res.json();
}

async function postRefresh(assetId) {
  let res;
  try {
    res = await fetchWithTimeout(`${API_BASE_URL}/sentiment/${assetId}/refresh`, { method: "POST" }, REFRESH_TIMEOUT_MS);
  } catch (e) {
    throw new ApiError(describeFetchError(e), { kind: e.name === "AbortError" ? "timeout" : "network" });
  }
  if (!res.ok) throw await failFrom(res, `Refresh for ${assetId}`);
}

// The hub mounts several widgets that all need the same two lists; share one request for a few seconds.
const SHARE_MS = 5000;
function shared(fn) {
  let at = 0;
  let pending = null;
  const wrapped = () => {
    if (!pending || Date.now() - at > SHARE_MS) {
      at = Date.now();
      pending = fn().catch((e) => {
        pending = null; // never cache a failure
        throw e;
      });
    }
    return pending;
  };
  wrapped.reset = () => { pending = null; };
  return wrapped;
}

const fetchAllSentimentRaw = shared(async () => {
  const data = await getJson("/sentiment", "Sentiment request");
  const seen = new Set();
  const unique = [];
  for (const item of Array.isArray(data) ? data : []) {
    const id = (item.asset_id || item.asset || "").toLowerCase();
    if (id && !seen.has(id)) {
      seen.add(id);
      unique.push(item);
    }
  }
  return unique;
});

/** Covered-universe rows (name, category, price, 24h change, held) keyed by lower-case symbol / slug. */
const loadMeta = shared(async () => {
  const rows = await fetchUniverse({ category: "all" });
  return new Map(rows.map((r) => [(r.type === "nft" ? r.id : r.symbol).toLowerCase(), r]));
});

const resetCaches = () => {
  fetchAllSentimentRaw.reset();
  loadMeta.reset();
};

/* ---------------- shaping ---------------- */

function normaliseRecord(raw) {
  return {
    assetId: (raw.asset_id || raw.asset || "").toLowerCase(),
    sentimentScore: raw.sentiment_score ?? 0,
    confidence: raw.confidence ?? 0,
    confidenceLabel: raw.confidence_label ?? "low",
    trend: raw.trend ?? "unknown",
    articleCount: raw.article_count ?? raw.post_count ?? 0,
    sourceCount: raw.source_count ?? 0,
    sourceBreakdown: raw.source_breakdown ?? { news_nlp: 0, market_signals: 0 },
    distribution: raw.sentiment_distribution ?? { positive: 0, negative: 0, neutral: 0 },
    topHeadlines: raw.top_headlines ?? [],
    marketSignals: raw.market_signals ?? {},
    articlesBySource: raw.articles_by_source ?? {},
    dataQuality: raw.data_quality ?? {},
    lastUpdated: raw.last_updated ?? raw.timestamp ?? null,
  };
}

// The engine writes a neutral placeholder (no articles) when it finds nothing; that isn't a reading.
const hasReading = (r) => r.articleCount > 0;

function metaFor(meta, assetId) {
  const m = meta.get(assetId);
  return {
    symbol: m?.symbol || assetId.toUpperCase(),
    name: m?.name || assetId.toUpperCase(),
    category: m?.type || "crypto",
    subcategory: m?.subcategory || null,
    held: !!m?.held,
    price: m?.price ?? null,
    changePct: m?.changePct ?? null,
  };
}

function moodLabel(score) {
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

const toScore100 = (s) => Math.round((s + 1) * 50);

export { confidenceLabelFromValue, evidencePhrase };
export { relativeTime } from "../utils/dateTime";

/* ---------------- public API ---------------- */

export const sentimentApi = {
  /**
   * Mood gauges for the hub header. Only crypto has a sentiment source, so `nft` and `realEstate`
   * are always null and `crypto` is null until the engine has produced a reading.
   */
  getMoodOverview: async () => {
    const records = (await fetchAllSentimentRaw()).map(normaliseRecord).filter(hasReading);
    if (!records.length) return { crypto: null, nft: null, realEstate: null };

    const avgScore = Math.round(records.reduce((s, r) => s + r.sentimentScore * 100, 0) / records.length);
    const avgConfidence = records.reduce((s, r) => s + r.confidence, 0) / records.length;
    return {
      crypto: {
        avgScore,
        label: moodLabel(avgScore),
        confidenceLabel: confidenceLabelFromValue(avgConfidence),
        assetCount: records.length,
        excludedCount: 0,
      },
      nft: null,
      realEstate: null,
    };
  },

  /** Average mood over time (0–100). Only crypto has history; other scopes are empty. */
  getMoodTrend: async (scope = "crypto", days = 30) => {
    const crypto = async () => {
      const rows = await getJson(`/sentiment/mood-trend?days=${encodeURIComponent(days)}`, "Mood trend request");
      return rows.map((r) => ({ date: r.date, value: toScore100(r.value) }));
    };
    if (scope === "both") return { crypto: await crypto(), nft: [], realEstate: [] };
    if (scope === "crypto") return crypto();
    return [];
  },

  /** Ranked asset list ("What stands out"). category: 'crypto' | 'nft' | 'all' */
  getAssetList: async (category = "crypto") => {
    const [raw, meta] = await Promise.all([fetchAllSentimentRaw(), loadMeta()]);
    const records = raw.map(normaliseRecord).filter(hasReading);

    const scored = records.map((r) => {
      const m = metaFor(meta, r.assetId);
      const score = toScore100(r.sentimentScore);
      return {
        assetId: r.assetId,
        name: m.name,
        symbol: m.symbol,
        category: m.category,
        subcategory: m.subcategory,
        held: m.held,
        score,
        readLabel: `${qualitativeLabel(score)}, ${evidencePhrase(r.confidenceLabel)}`,
        changePct: r.marketSignals?.price_change_24h ?? m.changePct ?? 0,
      };
    });

    // Everything else the platform covers is listed too, unscored, with its real 24h move.
    const scoredIds = new Set(scored.map((r) => r.assetId));
    const unscored = [...meta.entries()]
      .filter(([id]) => !scoredIds.has(id))
      .map(([id, m]) => ({
        assetId: id,
        name: m.name,
        symbol: m.symbol,
        category: m.type,
        subcategory: m.subcategory,
        held: !!m.held,
        score: null,
        readLabel: "No sentiment reading yet",
        changePct: m.changePct ?? 0,
      }));

    const all = [...scored, ...unscored];
    const filtered = category === "all" ? all : all.filter((r) => r.category === category);

    return filtered.sort((a, b) => {
      if (a.score == null) return 1;
      if (b.score == null) return -1;
      return b.score - a.score;
    });
  },

  /** Themes stored for the coverage (GET /sentiment/themes). */
  getThemes: async () => {
    const rows = await getJson("/sentiment/themes", "Themes request");
    return rows.map((t) => ({ label: t.label, direction: t.direction, category: t.category }));
  },

  /** Headlines behind the readings. There is no NFT news source, so that tab is empty. */
  getWhatWereReading: async (tab = "news") => {
    if (tab === "nft") return [];
    const records = (await fetchAllSentimentRaw()).map(normaliseRecord).filter(hasReading);
    const headlines = records.flatMap((r) => r.topHeadlines.map((h) => ({ ...h, assetId: r.assetId })));
    return headlines.sort((a, b) => (a.age_hours ?? 0) - (b.age_hours ?? 0));
  },

  /** Full detail for the asset drill-down. Throws a "not found" ApiError if there is no reading for the asset. */
  getAssetDetail: async (assetId) => {
    const [raw, meta] = await Promise.all([fetchAllSentimentRaw(), loadMeta()]);
    const record = raw.map(normaliseRecord).find((r) => r.assetId === assetId && hasReading(r));
    if (!record) {
      const name = metaFor(meta, assetId).name;
      throw new ApiError("No sentiment reading", { status: 404, kind: "notFound", detail: `There is no sentiment reading for ${name} yet.` });
    }

    const m = metaFor(meta, assetId);
    const sentimentScore = record.sentimentScore;
    const score = toScore100(sentimentScore);
    const headlines = record.topHeadlines;

    const d = record.distribution;
    const distTotal = Math.max(1, d.positive + d.neutral + d.negative);
    const pct = (n) => Math.round((n / distTotal) * 100);

    // A factual one-liner built from the reading itself.
    const narrative =
      `Based on ${record.articleCount} article${record.articleCount === 1 ? "" : "s"} from ${record.sourceCount} source${record.sourceCount === 1 ? "" : "s"}: ` +
      `${pct(d.positive)}% positive, ${pct(d.neutral)}% neutral, ${pct(d.negative)}% negative.`;

    return {
      assetId,
      symbol: m.symbol,
      name: m.name,
      category: m.category,
      subcategory: m.subcategory,
      held: m.held,
      price: m.price,
      priceChangePct: record.marketSignals?.price_change_24h ?? m.changePct,
      score,
      sentimentScore,
      label: qualitativeLabel(score) ?? "Neutral",
      confidencePct: Math.round(record.confidence * 100),
      confidenceLabel: record.confidenceLabel,
      narrative,
      trend: record.trend,
      distribution: { positive: pct(d.positive), neutral: pct(d.neutral), negative: pct(d.negative) },
      articleCount: record.articleCount,
      drivingFactors: headlines.slice(0, 3).map((h) => ({
        direction: (h.score ?? 0) >= 0 ? "up" : "down",
        title: h.title,
        description: [h.source, h.age_hours != null ? `${Math.round(h.age_hours)}h ago` : null].filter(Boolean).join(", "),
      })),
      headlines,
      sourceBreakdown: {
        newsPct: Math.round((record.sourceBreakdown.news_nlp ?? 0) * 100),
        marketPct: Math.round((record.sourceBreakdown.market_signals ?? 0) * 100),
      },
      articlesBySource: record.articlesBySource,
      marketSignals: {
        priceChange24h: record.marketSignals?.price_change_24h ?? m.changePct,
        volumeChange24h: record.marketSignals?.volume_change_24h ?? null,
        isTrending: record.marketSignals?.is_trending ?? null,
        btcDominance: record.marketSignals?.btc_dominance ?? null,
      },
      // Which inputs fell back to placeholders, so the UI can say so instead of passing them off as readings.
      dataQuality: {
        cmcKeyMissing: !!record.dataQuality.cmc_key_missing,
        cmcFallback: !!record.dataQuality.cmc_fallback,
        finbertUnavailable: !!record.dataQuality.finbert_unavailable,
      },
      lastUpdated: record.lastUpdated,
    };
  },

  /** An asset's sentiment over time (0–100). Empty until the engine has stored at least two readings. */
  getAssetOverTime: async (assetId, days = 30) => {
    const lookback = days === "24h" ? 1 : days; // the chart's "24h" option is one day of readings
    const json = await getJson(`/sentiment/${assetId}/history?days=${encodeURIComponent(lookback)}`, "History request");
    const history = json.history || [];
    if (history.length < 2) return [];
    return [...history].reverse().map((h) => ({
      date: h.last_updated || h.timestamp,
      value: toScore100(h.sentiment_score ?? 0),
    }));
  },

  /** Throws an ApiError if the refresh itself failed, so the UI can say so instead of re-showing old data. */
  refreshAsset: async (assetId) => {
    await postRefresh(assetId);
    resetCaches();
    return sentimentApi.getAssetDetail(assetId);
  },

  /** Refreshes every covered asset — used by the Hub's "Refresh Pipeline" button. */
  refreshAllActive: async () => {
    const ids = (await fetchAllSentimentRaw()).map((r) => (r.asset_id || r.asset || "").toLowerCase()).filter(Boolean);
    const results = await Promise.allSettled(ids.map((id) => postRefresh(id)));
    resetCaches();
    const failed = results.filter((r) => r.status === "rejected");
    if (failed.length === ids.length && ids.length > 0) throw failed[0].reason; // everything failed: surface the real cause
    if (failed.length > 0) {
      throw new ApiError(`${failed.length} of ${ids.length} assets could not be refreshed.`, {
        kind: "partial",
        detail: `${failed.length} of ${ids.length} assets could not be refreshed. The rest were updated.`,
      });
    }
  },

  getSwitchableAssets: async () => {
    const rows = await sentimentApi.getAssetList("all");
    return rows.filter((r) => r.score != null).map((r) => ({ id: r.assetId, name: r.name, symbol: r.symbol }));
  },

  /** Lower-case ids of everything on any of the signed-in user's watchlists ("Only my watchlist"). */
  getWatchedAssetIds: async () => {
    const lists = await watchlistApi.getInitialListsAsync();
    return new Set(lists.flatMap((l) => l.items.map((i) => String(i.id).toLowerCase())));
  },
};
