// NFT news sentiment card (sentiment_engine/nft_sentiment). Pure helpers, tested in nftSentiment.test.js.
// The backend score is -1..1; like the crypto sentiment screens it is shown as -100..100 with the same
// Bullish / Neutral / Bearish bands (sentimentApi.js moodLabel).

const isNum = (v) => typeof v === "number" && Number.isFinite(v);

export const NFT_MARKET_SLUG = "nft-market";

export function moodLabel(score100) {
  if (!isNum(score100)) return null;
  if (score100 >= 10) return "Bullish";
  if (score100 <= -10) return "Bearish";
  return "Neutral";
}

export function formatScore(score100) {
  if (!isNum(score100)) return "—";
  return score100 > 0 ? `+${score100}` : `${score100}`;
}

const TREND_TEXT = {
  improving: "Improving vs a day ago",
  deteriorating: "Worsening vs a day ago",
  stable: "Steady vs a day ago",
};

export function formatAge(hours) {
  if (!isNum(hours)) return "";
  if (hours < 1) return "under 1h ago";
  if (hours < 48) return `${Math.round(hours)}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

const to100 = (v) => (isNum(v) ? Math.round(v * 100) : null);
// news_nlp / market_signals are 0..1 (0.5 = neutral); shown on the same -100..100 scale as the score
const half100 = (v) => (isNum(v) ? Math.round((v * 2 - 1) * 100) : null);

/** Backend body (GET /nft/collections/{slug}/sentiment) -> what the card shows; null for no body. */
export function mapNftSentiment(d) {
  if (!d || typeof d !== "object") return null;
  const hasReading = d.status === "ok" && isNum(d.sentiment_score);
  const score = hasReading ? to100(d.sentiment_score) : null;
  const stories = isNum(d.story_count) ? d.story_count : 0;
  const articles = isNum(d.article_count) ? d.article_count : 0;
  const quality = d.data_quality || {};
  return {
    slug: d.slug,
    name: d.name,
    hasReading,
    score,
    scoreLabel: formatScore(score),
    mood: moodLabel(score),
    trendText: TREND_TEXT[d.trend] || null,
    confidenceLabel: d.confidence_label || "low",
    coverageLine: hasReading
      ? `${stories} ${stories === 1 ? "story" : "stories"}${articles > stories ? ` (${articles} articles)` : ""} from the last 7 days`
      : "",
    newsScore: half100(d.source_breakdown?.news_nlp),
    marketScore: half100(d.source_breakdown?.market_signals),
    headlines: (d.top_headlines || []).map((h) => ({
      title: h.title,
      link: typeof h.link === "string" && /^https?:\/\//.test(h.link) ? h.link : null,
      label: h.label || (h.score > 0 ? "positive" : h.score < 0 ? "negative" : "neutral"),
      reason: h.reason || "",
      source: h.source || "",
      age: formatAge(h.age_hours),
      moreOutlets: isNum(h.copies) && h.copies > 1 ? h.copies - 1 : 0,
    })),
    scorer: d.source || null,
    usedFallback: quality.llm_unavailable === true,
    validationNote: d.validation_note || "",
    lastUpdated: d.last_updated || null,
    stale: d.stale === true,
  };
}
