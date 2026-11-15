// Tests for the past ranges (ml/docs/DECISIONS.md D87-D89). Run: npm test. Hand-made numbers only; no network.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  MIN_CALIBRATION_DAYS, PAST_RANGES_CAPTION, PAST_RANGES_TOGGLE_LABEL, calibration, calibrationText, pastBandsForWindow,
} from "./pastRanges.js";
import { CONE_DAYS, Z_INNER, Z_OUTER } from "./volCone.js";

const cfg = readFileSync(new URL("../../../ml/config.py", import.meta.url), "utf8");
const cfgNumber = (name) => Number(cfg.match(new RegExp(`^${name}\\s*=\\s*([0-9.]+)`, "m"))[1]);

const day = (i) => new Date(Date.UTC(2026, 0, 1) + i * 86400000).toISOString().slice(0, 10);
const point = (i, close) => ({
  date: day(i), made_on: day(i - 30), inner_lower: 90, inner_upper: 110, outer_lower: 80, outer_upper: 120, close,
});
const historyOf = (n) => Array.from({ length: n }, (_, i) => ({ date: day(i), price: 100 }));

test("lag, z values and the minimum day count match the ML side (ml/config.py)", () => {
  assert.equal(cfgNumber("PAST_RANGE_LAG_DAYS"), CONE_DAYS);
  assert.equal(cfgNumber("CONE_Z_INNER"), Z_INNER);
  assert.equal(cfgNumber("CONE_Z_OUTER"), Z_OUTER);
  assert.equal(cfgNumber("PAST_RANGE_MIN_CALIBRATION_DAYS"), MIN_CALIBRATION_DAYS);
});

test("caption and toggle say what the owner asked for, with no model wording", () => {
  assert.equal(PAST_RANGES_CAPTION, "Shaded history: the range shown 30 days earlier for each day. Not a price prediction.");
  assert.equal(PAST_RANGES_TOGGLE_LABEL, "Show past ranges");
  assert.doesNotMatch(PAST_RANGES_CAPTION + PAST_RANGES_TOGGLE_LABEL, /ewma/i);
});

test("keeps only the points on visible dates, oldest first, and drops invalid ones", () => {
  const pts = [point(5, 100), point(2, 100), point(40, 100), { ...point(3, 100), close: null },
    { ...point(4, 100), inner_lower: 70 }];
  const bands = pastBandsForWindow({ points: pts }, historyOf(10));
  assert.deepEqual(bands.map((b) => b.date), [day(2), day(5)]);
  assert.deepEqual(bands[0], { date: day(2), inner: { lower: 90, upper: 110 }, outer: { lower: 80, upper: 120 }, close: 100 });
  assert.deepEqual(pastBandsForWindow(null, historyOf(10)), []);
  assert.deepEqual(pastBandsForWindow({ points: pts }, []), []);
});

test("calibration counts closes inside each band, bounds inclusive", () => {
  // 60 days: closes 100 (both), 110 (both, edge), 115 (80% only), 79 (neither), cycling.
  const closes = [100, 110, 115, 79];
  const bands = pastBandsForWindow({ points: Array.from({ length: 60 }, (_, i) => point(i, closes[i % 4])) }, historyOf(60));
  const c = calibration(bands);
  assert.equal(c.days, 60);
  assert.equal(c.share50, 30 / 60);
  assert.equal(c.share80, 45 / 60);
  assert.equal(calibrationText(c),
    "Over these 60 days, the price stayed inside the 80% range on 75% of days and inside the 50% range on 50%.");
});

test("shows nothing with fewer than 60 days", () => {
  const bands = pastBandsForWindow({ points: Array.from({ length: 59 }, (_, i) => point(i, 100)) }, historyOf(59));
  assert.equal(bands.length, 59);
  assert.equal(calibration(bands), null);
  assert.equal(calibrationText(null), null);
});
