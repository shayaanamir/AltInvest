import { apiFetch } from "./apiClient";
import { mapUniverseItem } from "./assetRepository";
import { getEvidencePhrase } from "../utils/scoring";

export function sentimentReadLabel(score) {
  if (score == null) return "No data";
  if (score >= 0.5) return "Strongly bullish";
  if (score >= 0.2) return "Bullish";
  if (score > -0.2) return "Neutral";
  if (score > -0.5) return "Bearish";
  return "Strongly bearish";
}

export const evidenceLabel = getEvidencePhrase;

export const compareApi = {
  /**
   * The picker's search (GET /compare/candidates): light rows, searched and ranked on the server,
   * best match first. Resolves to { items, total, maxSelectable }.
   */
  searchCandidates: async ({ q = "", category = "all", selected = [], limit = 30 } = {}) => {
    const p = new URLSearchParams({ q: q.trim().slice(0, 64), category, selected: selected.join(","), limit });
    const res = await apiFetch(`/compare/candidates?${p}`);
    return {
      items: res.items.map((r) => ({ ...mapUniverseItem(r), selected: r.selected })),
      total: res.total,
      maxSelectable: res.max_selectable,
    };
  },

  // Ids are a mix of crypto symbols and NFT slugs; the server works out which is which.
  getByIds: async (ids) => {
    if (ids.length < 2) return [];
    const res = await apiFetch(`/compare?ids=${encodeURIComponent(ids.join(","))}`);
    return res.items.map(mapUniverseItem);
  },
};
