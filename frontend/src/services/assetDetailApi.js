import { apiFetch } from "./apiClient";
import { formatAssetPrice, formatCurrencyCompact } from "../utils/formatters";
import { getAaiSignal, getRiskTone, getEvidencePhrase } from "../utils/scoring";
import { mapUniverseItem } from "./assetRepository";

export const deriveAaiSignal = getAaiSignal;
export const confidenceLabel = getEvidencePhrase;
export const riskLevelTone = getRiskTone;

function formatSupply(n) {
  if (n >= 1e9) return `${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  return n.toLocaleString();
}

// Only rows the database actually has a value for.
function buildMarketStats(m) {
  const rows = [
    m.market_rank != null && { label: "Market Rank", value: `#${m.market_rank} by Cap` },
    m.market_cap != null && { label: "Market Cap", value: formatCurrencyCompact(m.market_cap) },
    m.volume_24h != null && { label: "24h Volume", value: formatCurrencyCompact(m.volume_24h) },
    m.circulating_supply != null && { label: "Circulating Supply", value: formatSupply(m.circulating_supply) },
    m.all_time_high != null && { label: "All Time High", value: formatAssetPrice(m.all_time_high) },
  ];
  return rows.filter(Boolean);
}

function sentimentLabel(score) {
  return score > 0.1 ? "Positive" : score < -0.1 ? "Negative" : "Neutral";
}

export const assetDetailApi = {
  /** Resolves to null when the backend has no such asset (404); throws on any other failure. */
  getAssetDetail: async (symbol) => {
    let d;
    try {
      d = await apiFetch(`/assets/${encodeURIComponent(symbol)}/detail`);
    } catch (e) {
      if (e.status === 404) return null;
      throw e;
    }

    const h = d.header;
    return {
      symbol: d.symbol,
      header: {
        symbol: h.symbol,
        name: h.name,
        assetType: h.category,
        subcategory: h.subcategory,
        logoColor: h.logo_color || "var(--sv2-accent)",
        price: h.price,
        change24h: h.change_24h ?? 0,
        held: h.held,
        quantityHeld: h.quantity_held,
        watching: h.watching,
      },
      priceHistory: d.price_history,
      // Only the model's target point; the chart draws the branch from the last actual price.
      forecast: d.forecast ? d.forecast.points.slice(1) : null,
      // The target's band and how earlier runs turned out (runs whose target date has passed).
      forecastMeta: d.forecast && {
        lower: d.forecast.lower_bound,
        upper: d.forecast.upper_bound,
        changePct: d.forecast.change_30d_pct,
        confidence: d.forecast.confidence,
        modelVersion: d.forecast.model_version,
        meanAbsErrorPct: d.forecast.mean_abs_error_pct,
        scoredRuns: (d.forecast.runs || []).filter((x) => x.error_pct != null).length,
      },
      aaiPanel: d.aai_panel && {
        score: d.aai_panel.score,
        signal: d.aai_panel.signal,
        confidence: d.aai_panel.confidence,
      },
      riskOverview: d.risk_overview,
      marketStats: buildMarketStats(d.market_stats),
      sentimentSnippet: d.sentiment && {
        score: d.sentiment.score,
        label: sentimentLabel(d.sentiment.score),
        confidence: d.sentiment.confidence == null ? null : Math.round(d.sentiment.confidence * 100),
        trend: d.sentiment.trend,
      },
      about: d.about && {
        description: d.about.description,
        website: d.about.website,
        allTimeHigh: d.about.all_time_high,
        athDate: d.about.ath_date,
        source: d.about.source,
      },
      relatedAssets: (d.related || []).map(mapPeer),
      similarAssets: (d.similar || []).map(mapPeer),
    };
  },
};

// A related / similar asset card: the universe row plus why it was picked.
function mapPeer(s) {
        const m = mapUniverseItem(s);
        return {
          symbol: m.symbol,
          name: m.name,
          logoColor: m.color,
          price: m.price,
          change24h: m.change24h ?? 0,
          sparkline: m.sparkline,
          aaiScore: m.aaiScore,
          signal: m.signal,
          held: m.held,
          watching: m.watching,
          reason: s.reason || null,
        };
}
