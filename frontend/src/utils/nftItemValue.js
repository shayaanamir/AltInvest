// NFT item value card (Phase 10 step 10.7, ml/docs/DECISIONS.md D78). Pure helpers, tested in nftItemValue.test.js.
// ETH only (no USD conversion of the estimate), point estimate only (no range), no feature-importance drivers.

export const NFT_ITEM_CAPTION =
  "An estimate of what this item might sell for now, mostly driven by the collection floor and recent sales. Not a price prediction.";

const isNum = (v) => typeof v === "number" && Number.isFinite(v);

export function formatEth(v, digits = 3) {
  return isNum(v) ? `${v.toFixed(digits)} ETH` : "—";
}

// "2026-11-13T22:04:11Z" -> "13 Nov 2026" (UTC); anything else -> "—"
export function formatUtcDate(iso) {
  if (typeof iso !== "string" || !iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
}

/** Backend body (GET /nft/collections/{slug}/items/{token}/value) -> what the card shows. */
export function mapItemValue(d) {
  if (!d || typeof d !== "object") return null;
  const sale = d.last_sale && isNum(d.last_sale.price_eth) ? d.last_sale : null;
  const rank = isNum(d.rarity_rank) ? d.rarity_rank : null;
  const of = isNum(d.rarity_ranked_tokens) ? d.rarity_ranked_tokens : null;
  return {
    slug: d.slug,
    tokenId: String(d.token_id),
    estimate: isNum(d.estimated_value_eth) ? d.estimated_value_eth : null,
    estimateLabel: formatEth(d.estimated_value_eth),
    floorLabel: formatEth(d.last_floor_eth),
    floorDate: formatUtcDate(d.last_floor_time),
    lastSaleLabel: sale ? `${formatEth(sale.price_eth)} on ${formatUtcDate(sale.timestamp)}` : "No earlier sale in the data",
    noPriorSale: d.no_prior_sale === true,
    rarityLabel: rank != null ? `#${rank.toLocaleString("en-US")}${of != null ? ` of ${of.toLocaleString("en-US")}` : ""}` : "—",
    accuracyLine: `Typical error: ${d.accuracy_note || "Accuracy check pending"}`,
    note: d.note || null,
    stale: d.stale === true,
    method: d.method === "baseline_b2" ? "Similar-rarity sales (baseline)" : "Model",
    asOf: formatUtcDate(d.as_of),
  };
}

/** Holding row (GET /portfolio/holdings) -> the estimate line on the holdings card, or null. */
export function holdingEstimate(h) {
  if (!h || !isNum(h.estimated_value_eth)) return null;
  return {
    label: `Est. value ${formatEth(h.estimated_value_eth)}`,
    accuracyLine: `Typical error: ${h.estimated_value_accuracy_note || "Accuracy check pending"}`,
    asOf: formatUtcDate(h.estimated_value_as_of),
  };
}

/** A token id the backend accepts: digits only, at most 12. */
export function validTokenId(s) {
  const t = String(s ?? "").trim();
  return /^\d{1,12}$/.test(t) ? t : null;
}
