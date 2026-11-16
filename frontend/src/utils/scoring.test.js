import { test } from "node:test";
import assert from "node:assert/strict";
import { getAaiSignal, aaiRatingLabel, ratingClass, AAI_BADGE_LABEL } from "./scoring.js";

// Audit G-37: the AAI band is always shown as a rating, never as Buy/Sell advice.
const ADVICE = /\b(buy|sell|hold|reduce)\b/i;

test("AAI bands are rating words", () => {
  assert.deepEqual([80, 60, 50, 30, 10].map((s) => getAaiSignal(s).label),
    ["Very strong", "Strong", "Neutral", "Weak", "Very weak"]);
  assert.equal(getAaiSignal(null).label, "Neutral");
  for (const s of [0, 25, 45, 55, 75, 100]) assert.doesNotMatch(getAaiSignal(s).label, ADVICE);
});

test("API signal values map to rating words and keep their colours", () => {
  assert.deepEqual(["BUY", "HOLD", "SELL"].map(aaiRatingLabel), ["Strong", "Neutral", "Weak"]);
  assert.equal(aaiRatingLabel(null), null);
  assert.deepEqual(["Strong", "Neutral", "Weak", "SELL"].map(ratingClass), ["buy", "hold", "sell", "sell"]);
  for (const v of Object.values(AAI_BADGE_LABEL)) assert.doesNotMatch(v, ADVICE);
});
