import { test } from "node:test";
import assert from "node:assert/strict";
import { normaliseNftRecord, nftMoodOverview, nftSourceSplit, nftNarrative, nftMarketSignals } from "./nftSentimentHub.js";

const row = (slug, score, extra = {}) => ({
  slug, name: slug, status: "ok", sentiment_score: score, confidence: 0.6, confidence_label: "medium",
  article_count: 4, story_count: 3, source_count: 2, trend: "stable",
  source_breakdown: { news_nlp: 0.7, market_signals: 0.6 },
  sentiment_distribution: { positive: 2, neutral: 1, negative: 0 },
  market_signals: { price_change_24h: 1.5, price_change_7d: -4.2, activity_ratio: 1.3, as_of: "2026-11-15" },
  ...extra,
});
const placeholder = (slug) => ({ slug, name: slug, status: "no_articles", sentiment_score: null, confidence: 0, article_count: 0 });
const deps = { moodLabel: (s) => (s >= 10 ? "Bullish" : s <= -10 ? "Bearish" : "Neutral"), confidenceLabelFromValue: () => "medium" };

test("a placeholder has no articles, so the hub treats it as no reading", () => {
  const r = normaliseNftRecord(placeholder("azuki"));
  assert.equal(r.articleCount, 0);
  assert.equal(r.sentimentScore, 0);
  assert.equal(r.isNft, true);
});

test("the NFT mood is the average of collections with a reading, without the market row", () => {
  const records = [row("azuki", 0.4), row("milady", -0.2), placeholder("doodles-official"), row("nft-market", -0.9)]
    .map(normaliseNftRecord);
  const mood = nftMoodOverview(records, deps);
  assert.equal(mood.avgScore, 10);
  assert.equal(mood.assetCount, 2);
  assert.equal(mood.label, "Bullish");
  assert.equal(nftMoodOverview([normaliseNftRecord(placeholder("azuki"))], deps), null);
});

test("the source split shows the real blend weights", () => {
  assert.deepEqual(nftSourceSplit(normaliseNftRecord(row("azuki", 0.1))), { newsPct: 65, marketPct: 35 });
  const newsOnly = normaliseNftRecord(row("azuki", 0.1, { source_breakdown: { news_nlp: 0.6, market_signals: null } }));
  assert.deepEqual(nftSourceSplit(newsOnly), { newsPct: 100, marketPct: 0 });
});

test("the narrative counts stories and articles", () => {
  assert.equal(nftNarrative(normaliseNftRecord(row("azuki", 0.1))),
    "Based on 3 stories (4 articles) from 2 sources in the last 7 days: 67% positive, 33% neutral, 0% negative stories.");
  const one = normaliseNftRecord(row("azuki", 0.1, { article_count: 1, story_count: 1, source_count: 1,
    sentiment_distribution: { positive: 1, neutral: 0, negative: 0 } }));
  assert.equal(nftNarrative(one), "Based on 1 story from 1 source in the last 7 days: 100% positive, 0% neutral, 0% negative stories.");
});

test("market signals are the floor moves and sales pace", () => {
  assert.deepEqual(nftMarketSignals(normaliseNftRecord(row("azuki", 0.1))),
    { priceChange24h: 1.5, priceChange7d: -4.2, activityRatio: 1.3, asOf: "2026-11-15" });
  assert.deepEqual(nftMarketSignals(normaliseNftRecord(row("azuki", 0.1, { market_signals: {} }))),
    { priceChange24h: null, priceChange7d: null, activityRatio: null, asOf: null });
});
