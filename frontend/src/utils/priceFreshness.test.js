import { test } from "node:test";
import assert from "node:assert/strict";
import { priceAsOfLabel, delayedTitle } from "./priceFreshness.js";

const NOW = new Date("2026-11-17T10:00:00Z");

test("same UTC day shows the time only", () => {
  assert.equal(priceAsOfLabel("2026-11-17T09:58:12Z", NOW), "as of 09:58 UTC");
});

test("another day shows the date too", () => {
  assert.equal(priceAsOfLabel("2026-11-16T23:05:00Z", NOW), "as of 16 Nov, 23:05 UTC");
});

test("missing or bad time gives null", () => {
  assert.equal(priceAsOfLabel(null, NOW), null);
  assert.equal(priceAsOfLabel("not a date", NOW), null);
});

test("delayed tooltip names the time when known", () => {
  assert.equal(delayedTitle("2026-11-17T09:30:00Z", NOW), "This price has not updated for over 15 minutes (as of 09:30 UTC).");
  assert.equal(delayedTitle(null, NOW), "This price has not updated for over 15 minutes.");
});
