// NFT readings (GET /nft/sentiment) shaped for the Sentiment hub (services/sentimentApi.js), which was built
// for the crypto engine's records. Pure helpers, tested in nftSentimentHub.test.js.
//
// Scales follow the hub: the mood gauge and trend use -100..100, the asset list and detail use 0..100.

import { NFT_MARKET_SLUG } from "./nftSentiment.js";

const isNum = (v) => typeof v === "number" && Number.isFinite(v);

/** One stored NFT reading -> the hub's record shape (see sentimentApi.normaliseRecord), plus NFT extras. */
export function normaliseNftRecord(raw) {
  const real = raw?.status === "ok" && isNum(raw.sentiment_score);
  return {
    assetId: String(raw?.slug || "").toLowerCase(),
    isNft: true,
    isMarket: raw?.slug === NFT_MARKET_SLUG,
    name: raw?.name || raw?.slug || "",
    sentimentScore: real ? raw.sentiment_score : 0,
    confidence: real ? raw.confidence ?? 0 : 0,
    confidenceLabel: raw?.confidence_label ?? "low",
    trend: raw?.trend ?? "unknown",
    // A no-articles placeholder has 0 articles, so the hub's hasReading() leaves it out.
    articleCount: real ? raw.article_count ?? 0 : 0,
    storyCount: real ? raw.story_count ?? 0 : 0,
    sourceCount: raw?.source_count ?? 0,
    sourceBreakdown: raw?.source_breakdown ?? {},
    distribution: raw?.sentiment_distribution ?? { positive: 0, negative: 0, neutral: 0 },
    topHeadlines: raw?.top_headlines ?? [],
    marketSignals: raw?.market_signals ?? {},
    articlesBySource: raw?.articles_by_source ?? {},
    dataQuality: raw?.data_quality ?? {},
    scorer: raw?.source ?? null,
    validationNote: raw?.validation_note ?? "",
    lastUpdated: raw?.last_updated ?? null,
    stale: raw?.stale === true,
  };
}

/** NFT market mood gauge: the average of the collections that have a reading (the market pseudo-row excluded). */
export function nftMoodOverview(records, { moodLabel, confidenceLabelFromValue }) {
  const rows = records.filter((r) => !r.isMarket && r.articleCount > 0);
  if (!rows.length) return null;
  const avgScore = Math.round(rows.reduce((s, r) => s + r.sentimentScore * 100, 0) / rows.length);
  const avgConfidence = rows.reduce((s, r) => s + r.confidence, 0) / rows.length;
  return {
    avgScore,
    label: moodLabel(avgScore),
    confidenceLabel: confidenceLabelFromValue(avgConfidence),
    assetCount: rows.length,
    excludedCount: 0,
  };
}

/** The share of the reading that came from news vs floor/sales momentum: the real blend weights. */
export function nftSourceSplit(record) {
  const usedMarket = isNum(record.sourceBreakdown?.market_signals);
  return usedMarket ? { newsPct: 65, marketPct: 35 } : { newsPct: 100, marketPct: 0 };
}

/** Factual one-liner, counting stories (rewordings of one event are one story) as well as articles. */
export function nftNarrative(record) {
  const d = record.distribution;
  const total = Math.max(1, d.positive + d.neutral + d.negative);
  const pct = (n) => Math.round((n / total) * 100);
  const stories = record.storyCount || record.articleCount;
  const s = (n, one, many) => `${n} ${n === 1 ? one : many}`;
  const counted = record.articleCount > stories
    ? `${s(stories, "story", "stories")} (${s(record.articleCount, "article", "articles")})`
    : s(stories, "story", "stories");
  return `Based on ${counted} from ${s(record.sourceCount, "source", "sources")} in the last 7 days: ` +
    `${pct(d.positive)}% positive, ${pct(d.neutral)}% neutral, ${pct(d.negative)}% negative stories.`;
}

/** Market context for an NFT: floor moves and sales pace instead of the crypto volume / trending / BTC figures. */
export function nftMarketSignals(record) {
  const m = record.marketSignals || {};
  return {
    priceChange24h: isNum(m.price_change_24h) ? m.price_change_24h : null,
    priceChange7d: isNum(m.price_change_7d) ? m.price_change_7d : null,
    activityRatio: isNum(m.activity_ratio) ? m.activity_ratio : null,
    asOf: m.as_of || null,
  };
}
