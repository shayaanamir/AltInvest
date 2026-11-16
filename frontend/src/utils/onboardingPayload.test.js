import { test } from "node:test";
import assert from "node:assert/strict";

import { answersToPayload, marketsLabel, DEFAULT_RISK, DEFAULT_LAYOUT } from "./onboardingPayload.js";

test("untouched steps get the values the screens showed", () => {
  assert.deepEqual(answersToPayload({}), {
    skipped: false,
    answers: { markets: [], risk: DEFAULT_RISK, goals: [], assets: [], layout: DEFAULT_LAYOUT },
  });
  assert.equal(DEFAULT_RISK, 50);
  assert.equal(DEFAULT_LAYOUT, "ai-first");
});

test("chosen answers pass through unchanged, including the nfts key and the goal order", () => {
  const out = answersToPayload({
    markets: ["crypto", "nfts"], risk: 80, goals: ["trading", "longterm"], assets: ["BTC", "ETH"], layout: "analyst",
  });
  assert.deepEqual(out.answers, {
    markets: ["crypto", "nfts"], risk: 80, goals: ["trading", "longterm"], assets: ["BTC", "ETH"], layout: "analyst",
  });
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
  const out = answersToPayload({ markets: "crypto", goals: [1, "research", null], assets: undefined });
  assert.deepEqual(out.answers.markets, []);
  assert.deepEqual(out.answers.goals, ["research"]);
  assert.deepEqual(out.answers.assets, []);
});

test("a skip sends no answers, even when some were picked", () => {
  assert.deepEqual(answersToPayload({ markets: ["crypto"], risk: 90 }, { skipped: true }), { skipped: true, answers: {} });
});

test("markets read back as a label", () => {
  assert.equal(marketsLabel(["crypto", "nfts"]), "Crypto, NFTs");
  assert.equal(marketsLabel(["commodities", "tokenized", "mystery"]), "Commodities, Tokenized assets, mystery");
  assert.equal(marketsLabel([]), "");
  assert.equal(marketsLabel(undefined), "");
});
