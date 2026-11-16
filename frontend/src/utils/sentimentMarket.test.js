import { test } from "node:test";
import assert from "node:assert/strict";
import { sourceShare, marketNotice } from "./sentimentMarket.js";

test("the shares are the real blend weights, not the scores", () => {
  // news_nlp 0.63 / market 0.41 used to be shown as "63% news, 41% market"
  assert.deepEqual(sourceShare({ news_nlp: 0.63, market_signals: 0.41 }), { newsPct: 70, marketPct: 30 });
});

test("a news-only reading is 100% news", () => {
  assert.deepEqual(sourceShare({ news_nlp: 0.63, market_signals: null }), { newsPct: 100, marketPct: 0 });
  assert.deepEqual(sourceShare({}), { newsPct: 100, marketPct: 0 });
  assert.deepEqual(sourceShare(undefined), { newsPct: 100, marketPct: 0 });
});

test("complete market data needs no notice", () => {
  assert.equal(marketNotice({ degraded: false, market_unavailable: false }), null);
  assert.equal(marketNotice(), null);
});

test("no market data says the score is the news alone", () => {
  assert.match(marketNotice({ market_unavailable: true, quote_fallback: true }), /news alone/);
  assert.match(marketNotice({ quote_fallback: true }), /news alone/);
});

test("partial data names what is missing", () => {
  const n = marketNotice({ volume_fallback: true, trending_fallback: true });
  assert.match(n, /24h volume change/);
  assert.match(n, /whether it is trending/);
  assert.doesNotMatch(n, /news alone/);
});

test("readings stored before CoinGecko are flagged as placeholders", () => {
  assert.match(marketNotice({ cmc_fallback: true }), /before market data moved to CoinGecko/);
  assert.match(marketNotice({ cmc_key_missing: true }), /before market data moved to CoinGecko/);
});
