import { apiFetch } from "./apiClient";
import { fetchUniverse, mapUniverseItem } from "./assetRepository";
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
  // The picker universe is the same covered universe Discover browses.
  getUniverse: () => fetchUniverse({ category: "all", sort: "name", order: "asc" }),
  getAssetUniverse: () => fetchUniverse({ category: "all", sort: "name", order: "asc" }),

  search: (query) => fetchUniverse({ category: "all", sort: "name", order: "asc", q: query.trim() }),

  // Ids are a mix of crypto symbols and NFT slugs; the universe says which is which.
  getByIds: async (ids) => {
    const universe = await fetchUniverse({ category: "all" });
    const known = ids.map((id) => universe.find((a) => a.id === id)).filter(Boolean);
    if (known.length < 2) return known;
    const assets = known.filter((a) => a.type === "crypto").map((a) => a.id);
    const nft = known.filter((a) => a.type === "nft").map((a) => a.id);
    const res = await apiFetch(
      `/compare?assets=${encodeURIComponent(assets.join(","))}&nft=${encodeURIComponent(nft.join(","))}`
    );
    return res.items.map(mapUniverseItem);
  },
};
