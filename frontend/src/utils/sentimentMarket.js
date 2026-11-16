// How much of a crypto sentiment reading came from the news and how much from market data, and what to tell
// the user when part of the market data could not be fetched. Pure helpers, tested in sentimentMarket.test.js.
//
// The engine blends 70% news + 30% market (sentiment_engine utils/config.py). With no usable market data it
// reports market_signals: null and the score is the news alone; it never blends in a neutral placeholder.

export const CRYPTO_NEWS_WEIGHT = 70;
export const CRYPTO_MARKET_WEIGHT = 30;

const isNum = (v) => typeof v === "number" && Number.isFinite(v);

/** The real shares of the blend: 70/30, or 100/0 when the reading is the news alone. */
export function sourceShare(sourceBreakdown) {
  return isNum(sourceBreakdown?.market_signals)
    ? { newsPct: CRYPTO_NEWS_WEIGHT, marketPct: CRYPTO_MARKET_WEIGHT }
    : { newsPct: 100, marketPct: 0 };
}

/** One sentence for the Market context card when market data was missing, or null when it was complete. */
export function marketNotice(q = {}) {
  // Readings stored before CoinGecko replaced CoinMarketCap: their market half was a neutral 0.5.
  if (q.cmc_key_missing || q.cmc_fallback) {
    return "This reading was stored before market data moved to CoinGecko; its market half was a neutral placeholder. The next refresh replaces it.";
  }
  if (q.market_unavailable || q.quote_fallback) {
    return "Market data could not be fetched for this read, so the score is the news alone. Missing figures are shown as —.";
  }
  const missing = [];
  if (q.global_fallback) missing.push("the overall market change");
  if (q.volume_fallback) missing.push("the 24h volume change");
  if (q.trending_fallback) missing.push("whether it is trending");
  return missing.length
    ? `Part of the market data was unavailable (${missing.join(", ")}); the market score uses what could be fetched. Missing figures are shown as —.`
    : null;
}
