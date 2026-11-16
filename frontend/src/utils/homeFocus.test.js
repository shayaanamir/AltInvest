import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import {
  DEFAULT_FOCUS, FOCUS_PRESETS, WIDGET_LABELS, normalizeFocus, getFocus, focusLandingPage, dashboardRows, rowKind,
} from "./homeFocus.js";

const LANDING_PAGES = ["Dashboard", "Portfolio", "Discover", "Sentiment"];

test("there are four presets and the default is one of them", () => {
  assert.deepEqual(FOCUS_PRESETS.map((p) => p.key), ["everything", "portfolio", "markets", "sentiment"]);
  assert.equal(DEFAULT_FOCUS, "everything");
});

test("every preset has a label, a landing page we can open, and only known widgets", () => {
  for (const p of FOCUS_PRESETS) {
    assert.ok(p.label && p.blurb && p.description, p.key);
    assert.ok(LANDING_PAGES.includes(p.landing), `${p.key} lands on ${p.landing}`);
    for (const row of p.rows) {
      assert.ok(row.length >= 1 && row.length <= 2, `${p.key} row size`);
      for (const id of row) assert.ok(WIDGET_LABELS[id], `${p.key} uses unknown widget ${id}`);
    }
  }
});

test("a dashboard is never empty, always opens with the stats, and never repeats a widget", () => {
  for (const p of FOCUS_PRESETS) {
    const ids = p.rows.flat();
    assert.equal(ids[0], "stats", p.key);
    assert.ok(ids.length >= 3, `${p.key} shows at least one data section besides the stats`);
    assert.equal(new Set(ids).size, ids.length, `${p.key} repeats a widget`);
  }
});

test("each non-default preset really differs from the default dashboard", () => {
  const base = JSON.stringify(dashboardRows("everything"));
  for (const p of FOCUS_PRESETS.filter((x) => x.key !== "everything")) {
    assert.notEqual(JSON.stringify(p.rows), base, p.key);
    assert.notEqual(p.landing, "Dashboard", `${p.key} should land somewhere other than the dashboard`);
  }
});

test("the default preset is today's dashboard", () => {
  assert.deepEqual(dashboardRows("everything"), [["stats"], ["performance", "insights"], ["assets", "collections"]]);
  assert.equal(focusLandingPage("everything"), "Dashboard");
});

test("old or unknown stored values read as the default", () => {
  for (const old of ["minimal", "analyst", "trader", "ai-first", "", null, undefined, 42, "constructor", "__proto__"]) {
    assert.equal(normalizeFocus(old), DEFAULT_FOCUS, String(old));
  }
  assert.equal(getFocus("trader").key, "everything");
  assert.equal(normalizeFocus("markets"), "markets");
});

test("landing pages by focus", () => {
  assert.equal(focusLandingPage("portfolio"), "Portfolio");
  assert.equal(focusLandingPage("markets"), "Discover");
  assert.equal(focusLandingPage("sentiment"), "Sentiment");
  assert.equal(focusLandingPage("nonsense"), "Dashboard");
});

test("row kinds pick the right dashboard grid", () => {
  assert.equal(rowKind(["stats"]), "stats");
  assert.equal(rowKind(["performance", "insights"]), "main");
  assert.equal(rowKind(["insights"]), "main");
  assert.equal(rowKind(["assets", "collections"]), "bottom");
  assert.equal(rowKind(["assets"]), "bottom");
});

test("the backend knows the same focus keys and landing pages", () => {
  const py = readFileSync(new URL("../../../backend/routes/profile.py", import.meta.url), "utf8");
  const block = py.match(/FOCUS_LANDING\s*=\s*\{([^}]*)\}/);
  assert.ok(block, "FOCUS_LANDING not found in backend/routes/profile.py");
  const backend = Object.fromEntries([...block[1].matchAll(/"(\w+)"\s*:\s*"(\w+)"/g)].map((m) => [m[1], m[2]]));
  const frontend = Object.fromEntries(FOCUS_PRESETS.map((p) => [p.key, p.landing]));
  assert.deepEqual(backend, frontend);
});
