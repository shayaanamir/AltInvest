import { test } from "node:test";
import assert from "node:assert/strict";
import { mapNftSentiment, moodLabel, formatScore, formatAge } from "./nftSentiment.js";

const BODY = {
  slug: "boredapeyachtclub", name: "Bored Ape Yacht Club", status: "ok", sentiment_score: -0.3186,
  source: "LLM (gpt-oss-120b on Groq)", confidence: 1.0, confidence_label: "high", trend: "deteriorating",
  last_updated: "2026-11-16T01:05:53Z", stale: false, article_count: 17, story_count: 10,
  source_breakdown: { news_nlp: 0.25, market_signals: 0.6 },
  top_headlines: [
    { title: "Machi sells 31 BAYC at a loss", score: -0.6, contribution: -0.1, label: "negative",
      reason: "Large loss sale", source: "Pluang", copies: 3, age_hours: 96.7, link: "https://news.google.com/x" },
    { title: "Holder count near one-year high", score: 0.6, contribution: 0.05, label: "positive",
      reason: "", source: "TokenPost", copies: 1, age_hours: 0.4, link: "javascript:alert(1)" },
  ],
  data_quality: { llm_unavailable: false }, validated: false, validation_note: "Not validated.",
};

test("the score is shown on the crypto screens' -100..100 scale with their mood bands", () => {
  const s = mapNftSentiment(BODY);
  assert.equal(s.score, -32);
  assert.equal(s.scoreLabel, "-32");
  assert.equal(s.mood, "Bearish");
  assert.equal(moodLabel(10), "Bullish");
  assert.equal(moodLabel(9), "Neutral");
  assert.equal(moodLabel(-10), "Bearish");
  assert.equal(formatScore(35), "+35");
  assert.equal(formatScore(0), "0");
});

test("coverage counts stories, with the article count when outlets repeated them", () => {
  assert.equal(mapNftSentiment(BODY).coverageLine, "10 stories (17 articles) from the last 7 days");
  assert.equal(mapNftSentiment({ ...BODY, story_count: 1, article_count: 1 }).coverageLine, "1 story from the last 7 days");
});

test("news and market parts are shown on the same scale", () => {
  const s = mapNftSentiment(BODY);
  assert.equal(s.newsScore, -50);
  assert.equal(s.marketScore, 20);
  assert.equal(mapNftSentiment({ ...BODY, source_breakdown: { news_nlp: 0.5, market_signals: null } }).marketScore, null);
});

test("headlines keep only http(s) links and say how many other outlets ran the story", () => {
  const [a, b] = mapNftSentiment(BODY).headlines;
  assert.equal(a.link, "https://news.google.com/x");
  assert.equal(a.moreOutlets, 2);
  assert.equal(a.age, "4d ago");
  assert.equal(b.link, null);
  assert.equal(b.moreOutlets, 0);
  assert.equal(b.age, "under 1h ago");
});

test("a no-articles reading has no score", () => {
  const s = mapNftSentiment({ ...BODY, status: "no_articles", sentiment_score: null, story_count: 0 });
  assert.equal(s.hasReading, false);
  assert.equal(s.score, null);
  assert.equal(s.mood, null);
  assert.equal(s.scoreLabel, "—");
});

test("trend text, fallback flag and missing body", () => {
  assert.equal(mapNftSentiment(BODY).trendText, "Worsening vs a day ago");
  assert.equal(mapNftSentiment({ ...BODY, trend: "unknown" }).trendText, null);
  assert.equal(mapNftSentiment({ ...BODY, data_quality: { llm_unavailable: true } }).usedFallback, true);
  assert.equal(mapNftSentiment(null), null);
  assert.equal(formatAge(30), "30h ago");
});
