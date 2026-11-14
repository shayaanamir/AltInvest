// Tests for the NFT floor cone (ml/docs/DECISIONS.md D52 amended, D67). Run: npm test. Hand-made numbers only.
import { test } from "node:test";
import assert from "node:assert/strict";
import { Z_OUTER, buildCone, coneFromVol, dailyVol } from "./volCone.js";
import {
  NFT_CONE_CAPTION, NFT_ETH_ONLY_CONE_NOTE, NFT_RISK_RELATIVE_NOTE, ethOnlyCone, floorPoints, floorStaleness,
  nftChartLayers, nftConeHiddenReason, nftConeStartLabel,
} from "./nftCone.js";

const NOTE = "Risk model: 30-day floor volatility (persistence) ... not comparable to crypto risk scores.";
const risk = (over = {}) => ({ volatility: 0.9, note: NOTE, modelVersion: "nft-persistence-pooled-pct", isIlliquid: false, ...over });
const history = [
  { date: "2026-11-08", floor_eth: 0.46, floor_usd: 1030.4 },
  { date: "2026-11-09", floor_eth: null, floor_usd: null },
  { date: "2026-11-10", floor_eth: 0.45, floor_usd: 956.5 },
];
const close = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, `${a} != ${b}`);

test("draws the cone for a served NFT volatility, from the last floor, with the same math as crypto", () => {
  const pts = floorPoints(history, "ETH");
  assert.deepEqual(pts.map((p) => p.date), ["2026-11-08", "2026-11-10"]);       // the gap day is left out
  const { layers, cone, hidden } = nftChartLayers(pts, risk());
  assert.deepEqual(layers, ["history", "cone-outer", "cone-inner"]);
  assert.equal(hidden, null);
  assert.equal(cone.length, 31);
  close(cone[0].outer.upper, 0.45);
  close(Math.log(cone[30].outer.upper / 0.45), Z_OUTER * dailyVol(0.9) * Math.sqrt(30));
  assert.deepEqual(cone, coneFromVol(pts[1], 0.9));
});

test("hides the cone when the volatility is missing, null, zero or not a number", () => {
  for (const v of [undefined, null, 0, -1, NaN, "0.9"]) {
    const { layers, cone } = nftChartLayers(floorPoints(history, "ETH"), risk({ volatility: v }));
    assert.deepEqual(layers, ["history"]);
    assert.equal(cone, null);
  }
  assert.equal(nftConeHiddenReason(null), "no risk data");
});

test("hides the cone when the data is stale (ML 48 h or backend 36 h note) or the collection is illiquid", () => {
  const stale = risk({ note: `${NOTE} data stale: the newest stored row is 37 h old (backend limit 36 h).` });
  assert.equal(nftConeHiddenReason(stale), "data stale");
  assert.equal(nftConeHiddenReason(risk({ note: `${NOTE} data stale: last floor 2026-11-08` })), "data stale");
  assert.equal(nftConeHiddenReason(risk({ isIlliquid: true })), "illiquid");
  assert.deepEqual(nftChartLayers(floorPoints(history, "ETH"), risk({ isIlliquid: true })).layers, ["history"]);
});

test("draws for the served persistence vol, which no risk model replaced (D52 amended, D73)", () => {
  const persistence = risk({ modelVersion: "nft-persistence-pooled-pct", note: "Risk model: 30-day floor volatility (persistence)." });
  assert.equal(nftConeHiddenReason(persistence), null);
  assert.equal(buildCone({ date: "2026-11-10", price: 1 }, { volatility: 0.9, note: persistence.note }), null); // crypto gate differs
  assert.equal(nftConeHiddenReason(risk({ modelVersion: "seed-v1" })), "not an ML NFT value");
});

test("the USD view never draws a cone; a separate ETH-only cone is shown instead (D67 revised)", () => {
  const usd = nftChartLayers(floorPoints(history, "USD"), risk(), "USD");
  assert.deepEqual(usd.layers, ["history"]);
  assert.equal(usd.cone, null);
  const eth = ethOnlyCone(history, risk());
  assert.deepEqual(eth.layers, ["history", "cone-outer", "cone-inner"]);
  close(eth.cone[0].outer.upper, 0.45);                                       // starts at the last ETH floor
  assert.equal(NFT_ETH_ONLY_CONE_NOTE, "This range is in ETH. ETH price moves are not included.");
  const long = Array.from({ length: 60 }, (_, i) => ({ date: `2026-09-${String((i % 28) + 1).padStart(2, "0")}`, floor_eth: 1 }));
  assert.equal(ethOnlyCone(long, risk()).cone.length, 31);
});

test("stale indicator: the newest floor point is more than 3 days old, or the newest floor is missing (D67h)", () => {
  const rows = [
    { date: "2026-11-08", floor_eth: 0.46, floor_age_hours: 10 },
    { date: "2026-11-09", floor_eth: null, floor_age_hours: 80 },
    { date: "2026-11-10", floor_eth: 0.45, floor_age_hours: 9 },
  ];
  assert.deepEqual(floorStaleness(rows), { stale: false, latestAgeDays: 9 / 24, staleDaysInRange: 1 });
  assert.equal(floorStaleness([...rows.slice(0, 2), { date: "2026-11-10", floor_eth: 0.45, floor_age_hours: 73 }]).stale, true);
  assert.equal(floorStaleness([{ date: "2026-11-10", floor_eth: null, floor_age_hours: 49 }]).stale, true);
  assert.equal(floorStaleness([{ date: "2026-11-10", floor_eth: 0.4, floor_age_hours: 72 }]).stale, false);
  assert.deepEqual(floorStaleness([]), { stale: false, latestAgeDays: null, staleDaysInRange: 0 });
});

test("never a forecast or center line, and the labels and captions the plan requires", () => {
  const { layers } = nftChartLayers(floorPoints(history, "ETH"), risk());
  assert.ok(!layers.some((l) => /forecast|center|predict/.test(l)));
  assert.deepEqual(nftChartLayers(floorPoints(history.slice(0, 1), "ETH"), risk()).layers, []);
  assert.equal(nftConeStartLabel("2026-11-10"), "Last floor, 10 Nov");
  assert.equal(NFT_CONE_CAPTION, "Likely floor range based on recent volatility, not a price prediction.");
  assert.match(NFT_RISK_RELATIVE_NOTE, /relative to the other NFT collections/);
  assert.match(NFT_RISK_RELATIVE_NOTE, /not comparable to crypto risk scores/);
});
