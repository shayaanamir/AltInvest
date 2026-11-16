import { test } from "node:test";
import assert from "node:assert/strict";

import { answersToPayload, marketsLabel, togglePick, DEFAULT_RISK, DEFAULT_DENSITY, MAX_PICKS } from "./onboardingPayload.js";

test("untouched steps get the values the screens showed", () => {
  assert.deepEqual(answersToPayload({}), {
    skipped: false,
    answers: { markets: [], risk: DEFAULT_RISK, goals: [], assets: [], nfts: [], focus: "everything", density: DEFAULT_DENSITY },
  });
  assert.equal(DEFAULT_RISK, 50);
  assert.equal(DEFAULT_DENSITY, "comfortable");
});

test("chosen answers pass through unchanged, including the goal order", () => {
  const out = answersToPayload({
    markets: ["crypto", "nfts"], risk: 80, goals: ["trading", "longterm"], assets: ["BTC", "ETH"], nfts: ["azuki"],
    focus: "markets", density: "compact",
  }, { theme: "light" });
  assert.deepEqual(out.answers, {
    markets: ["crypto", "nfts"], risk: 80, goals: ["trading", "longterm"], assets: ["BTC", "ETH"], nfts: ["azuki"],
    focus: "markets", density: "compact", theme: "light",
  });
});

test("the theme in use is sent; anything else is left out", () => {
  assert.equal(answersToPayload({}, { theme: "dark" }).answers.theme, "dark");
  assert.equal("theme" in answersToPayload({}, { theme: "blue" }).answers, false);
  assert.equal("theme" in answersToPayload({}).answers, false);
});

test("an old or unknown focus becomes the default, and density only allows the two values", () => {
  assert.equal(answersToPayload({ focus: "trader" }).answers.focus, "everything");
  assert.equal(answersToPayload({ focus: "sentiment" }).answers.focus, "sentiment");
  assert.equal(answersToPayload({ density: "tiny" }).answers.density, "comfortable");
});

test("risk is rounded and kept within 0-100; a bad value falls back to the default", () => {
  assert.equal(answersToPayload({ risk: 33.6 }).answers.risk, 34);
  assert.equal(answersToPayload({ risk: 250 }).answers.risk, 100);
  assert.equal(answersToPayload({ risk: -5 }).answers.risk, 0);
  assert.equal(answersToPayload({ risk: 0 }).answers.risk, 0);       // 0 is an answer, not "unset"
  assert.equal(answersToPayload({ risk: "high" }).answers.risk, DEFAULT_RISK);
  assert.equal(answersToPayload({ risk: NaN }).answers.risk, DEFAULT_RISK);
});

test("non-list or non-string entries are dropped rather than sent", () => {
  const out = answersToPayload({ markets: "crypto", goals: [1, "research", null], assets: undefined, nfts: [{}, "doodles"] });
  assert.deepEqual(out.answers.markets, []);
  assert.deepEqual(out.answers.goals, ["research"]);
  assert.deepEqual(out.answers.assets, []);
  assert.deepEqual(out.answers.nfts, ["doodles"]);
});

test("picks are capped at what the server accepts", () => {
  const many = Array.from({ length: 80 }, (_, i) => `C${i}`);
  assert.equal(answersToPayload({ assets: many, nfts: many }).answers.assets.length, MAX_PICKS);
  assert.equal(answersToPayload({ assets: many, nfts: many }).answers.nfts.length, MAX_PICKS);
});

test("a skip sends no answers, even when some were picked", () => {
  assert.deepEqual(answersToPayload({ markets: ["crypto"], risk: 90 }, { skipped: true, theme: "dark" }), { skipped: true, answers: {} });
});

test("togglePick adds, removes, keeps order and respects the cap", () => {
  assert.deepEqual(togglePick(undefined, "BTC"), ["BTC"]);
  assert.deepEqual(togglePick(["BTC"], "ETH"), ["BTC", "ETH"]);
  assert.deepEqual(togglePick(["BTC", "ETH"], "BTC"), ["ETH"]);
  const full = Array.from({ length: 3 }, (_, i) => `C${i}`);
  assert.deepEqual(togglePick(full, "X", 3), full);                  // full: a new pick is ignored
  assert.deepEqual(togglePick(full, "C1", 3), ["C0", "C2"]);         // but a pick can still be removed
});

test("markets read back as a label", () => {
  assert.equal(marketsLabel(["crypto", "nfts"]), "Crypto, NFTs");
  assert.equal(marketsLabel(["nfts"]), "NFTs");
  assert.equal(marketsLabel(["commodities"]), "commodities");        // an old saved value still shows something
  assert.equal(marketsLabel([]), "");
  assert.equal(marketsLabel(undefined), "");
});
