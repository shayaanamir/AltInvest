import { test } from "node:test";
import assert from "node:assert/strict";
import { NFT_ITEM_CAPTION, mapItemValue, holdingEstimate, validTokenId, formatUtcDate } from "./nftItemValue.js";

const BODY = {
  slug: "pudgypenguins", token_id: "7862", estimated_value_eth: 9.87654, method: "model", last_floor_eth: 9.5,
  last_floor_time: "2026-11-13T22:04:11Z", last_sale: { price_eth: 4.32, timestamp: "2026-06-01T10:00:00Z" },
  no_prior_sale: false, rarity_rank: 1234, rarity_ranked_tokens: 8888,
  accuracy_note: "Median error in testing (Feb-Nov 2026): 2.0%", rarity_accuracy_note: null,
  model_version: "nft-fv-pooled-l1-nl15-dev-2025-12-25", note: null, as_of: "2026-11-14T00:16:00Z", stale: false,
};

test("the caption is the agreed text", () => {
  assert.equal(NFT_ITEM_CAPTION,
    "An estimate of what this item might sell for now, mostly driven by the collection floor and recent sales. Not a forecast of future price.");
});

test("the card shows the estimate in ETH, the last floor with its date, the last sale and the rarity rank", () => {
  const v = mapItemValue(BODY);
  assert.equal(v.estimateLabel, "9.877 ETH");
  assert.equal(v.floorLabel, "9.500 ETH");
  assert.equal(v.floorDate, "13 Nov 2026");
  assert.equal(v.lastSaleLabel, "4.320 ETH on 1 Jun 2026");
  assert.equal(v.rarityLabel, "#1,234 of 8,888");
  assert.equal(v.method, "Model");
  assert.ok(!JSON.stringify(v).includes("$") && !JSON.stringify(v).toLowerCase().includes("usd"));  // ETH only
});

test("the error lines are the served notes as they come (D84)", () => {
  assert.equal(mapItemValue(BODY).accuracyLine, "Median error in testing (Feb-Nov 2026): 2.0%");
  assert.equal(mapItemValue(BODY).rarityAccuracyLine, null);
  const rare = mapItemValue({ ...BODY, rarity_accuracy_note: "Rarest items: about 9%" });
  assert.equal(rare.rarityAccuracyLine, "Rarest items: about 9%");
  assert.equal(mapItemValue({ ...BODY, accuracy_note: "" }).accuracyLine, "Accuracy check pending");
});

test("no range and no drivers are shown, whatever the body carries", () => {
  const v = mapItemValue({ ...BODY, lower_eth: 1, upper_eth: 2, drivers: [{ f: "x" }] });
  for (const k of Object.keys(v)) assert.ok(!/lower|upper|range|driver/i.test(k), k);
});

test("an item without an earlier sale, a missing estimate, B2 and a stale row", () => {
  const v = mapItemValue({ ...BODY, last_sale: null, no_prior_sale: true, estimated_value_eth: null,
    method: "baseline_b2", stale: true, note: "No floor price before now, so no estimate." });
  assert.equal(v.lastSaleLabel, "No earlier sale in the data");
  assert.equal(v.noPriorSale, true);
  assert.equal(v.estimateLabel, "—");
  assert.equal(v.method, "Similar-rarity sales (baseline)");
  assert.equal(v.stale, true);
  assert.equal(mapItemValue(null), null);
});

test("holding estimate line and token id validation", () => {
  assert.deepEqual(holdingEstimate({ estimated_value_eth: 0.84,
    estimated_value_accuracy_note: "Median error in testing (Feb-Nov 2026): 3.8%",
    estimated_value_rarity_accuracy_note: "Rarest items: about 9%", estimated_value_as_of: "2026-11-14T00:16:00Z" }),
  { label: "Est. value 0.840 ETH", accuracyLine: "Median error in testing (Feb-Nov 2026): 3.8%",
    rarityAccuracyLine: "Rarest items: about 9%", asOf: "14 Nov 2026" });
  assert.equal(holdingEstimate({ estimated_value_eth: null }), null);
  assert.equal(validTokenId(" 7862 "), "7862");
  assert.equal(validTokenId("12a"), null);
  assert.equal(validTokenId(""), null);
  assert.equal(formatUtcDate("nope"), "—");
});
