// Tests for the volatility cone (ml/docs/DECISIONS.md D52). Run: npm test  (node --test, no extra packages).
// Hand-made numbers only; no network.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  ANNUALISATION_DAYS, CONE_CAPTION, CONE_DAYS, Z_INNER, Z_OUTER,
  buildCone, chartLayers, coneBand, coneVolatility, dailyVol,
} from "./volCone.js";

const EWMA_NOTE = "Risk model: EWMA volatility (lambda 0.94), which beat 30-day persistence (D50, D51).";
const risk = (volatility, note = EWMA_NOTE) => ({ volatility, note });
const history = [
  { date: "2026-11-01", price: 100 },
  { date: "2026-11-02", price: 104 },
];
const close = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, `${a} != ${b}`);

test("uses the annualisation factor serving uses (ml/config.py)", () => {
  const cfg = readFileSync(new URL("../../../ml/config.py", import.meta.url), "utf8");
  const served = Number(cfg.match(/^ANNUALISATION_DAYS\s*=\s*(\d+)/m)[1]);
  assert.equal(ANNUALISATION_DAYS, served);
  close(dailyVol(0.365), 0.365 / Math.sqrt(served));
  const cone = buildCone(history[1], risk(0.5));
  const sd = 0.5 / Math.sqrt(served);
  close(Math.log(cone[1].outer.upper / 104), Z_OUTER * sd);
});

test("width is 0 at d = 0, so the cone joins the history line", () => {
  const cone = buildCone(history[1], risk(0.6));
  assert.equal(cone[0].d, 0);
  assert.equal(cone[0].date, "2026-11-02");
  for (const band of [cone[0].inner, cone[0].outer]) {
    assert.equal(band.lower, 104);
    assert.equal(band.upper, 104);
  }
});

test("symmetric in log space and widens with sqrt(d)", () => {
  const sd = dailyVol(0.6);
  for (const d of [1, 4, 9, 30]) {
    for (const z of [Z_INNER, Z_OUTER]) {
      const b = coneBand(104, sd, d, z);
      close(Math.log(b.upper / 104), -Math.log(b.lower / 104));
      close(Math.log(b.upper / 104), Math.log(coneBand(104, sd, 1, z).upper / 104) * Math.sqrt(d));
    }
  }
  const cone = buildCone(history[1], risk(0.6));
  assert.equal(cone.length, CONE_DAYS + 1);
  assert.equal(cone[CONE_DAYS].date, "2026-12-02");                    // 30 days past the last history date
  assert.ok(cone[CONE_DAYS].outer.upper > cone[CONE_DAYS].inner.upper); // outer 80% band wider than inner 50%
});

test("cone is hidden when volatility is missing, null, not positive, not the EWMA model, or stale", () => {
  for (const r of [null, undefined, risk(null), risk(undefined), risk(Number.NaN), risk(0), risk(-0.1), risk("0.5"),
    risk(0.5, "mock data — no risk score found in DB yet"), risk(0.5, null),
    risk(0.5, `${EWMA_NOTE} data stale: the newest stored row is 40 h old`)]) {
    assert.equal(coneVolatility(r), null);
    assert.equal(buildCone(history[1], r), null);
    assert.deepEqual(chartLayers(history, r).layers, ["history"]);
  }
  assert.equal(coneVolatility(risk(0.5)), 0.5);
});

test("no forecast or center line is ever a chart layer", () => {
  assert.deepEqual(chartLayers(history, risk(0.5)).layers, ["history", "cone-outer", "cone-inner"]);
  assert.deepEqual(chartLayers(history.slice(0, 1), risk(0.5)).layers, []);
  const src = readFileSync(new URL("../components/assetDetail/PricePerformanceCard.jsx", import.meta.url), "utf8");
  assert.doesNotMatch(src, /forecastPath|forecastPts|safeForecast|forecastMeta|lower_bound|upper_bound/);
  assert.doesNotMatch(src, /strokeDasharray="6,5"/);                   // the old dashed forecast line
  assert.match(src, /chartLayers\(/);
  assert.ok(src.includes("{CONE_CAPTION}"));
  assert.equal(CONE_CAPTION, "Likely price range based on recent volatility, not a price prediction.");
});
