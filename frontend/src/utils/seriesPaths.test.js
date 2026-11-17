import { test } from "node:test";
import assert from "node:assert/strict";

import { buildSeriesPaths } from "./seriesPaths.js";

test("fewer than two points draw nothing", () => {
  assert.equal(buildSeriesPaths(undefined, 100, 50), null);
  assert.equal(buildSeriesPaths([], 100, 50), null);
  assert.equal(buildSeriesPaths([5], 100, 50), null);
});

test("points are spread evenly across the padded width and kept inside the padded height", () => {
  const out = buildSeriesPaths([1, 2, 3], 100, 50, { padLeft: 10, padRight: 10, padTop: 5, padBottom: 5 });
  assert.deepEqual(out.pts.map((p) => p.x), [10, 50, 90]);
  for (const p of out.pts) assert.ok(p.y >= 5 && p.y <= 45, `y ${p.y} outside the plot`);
  assert.ok(out.pts[0].y > out.pts[2].y, "a rising series ends higher (smaller y) than it starts");
  assert.deepEqual(out.last, out.pts[2]);
});

test("values and { value } points give the same path", () => {
  const a = buildSeriesPaths([10, 20, 15], 120, 60);
  const b = buildSeriesPaths([{ value: 10 }, { value: 20 }, { value: 15 }], 120, 60);
  assert.equal(a.linePath, b.linePath);
  assert.equal(a.areaPath, b.areaPath);
});

test("the line starts with a move and the area closes along the bottom", () => {
  const out = buildSeriesPaths([1, 3, 2], 100, 50, { padBottom: 10 });
  assert.ok(out.linePath.startsWith("M "));
  assert.ok(out.areaPath.endsWith("Z"));
  assert.ok(out.areaPath.includes(` ${50 - 10} `), "the area drops to the bottom padding");
});

test("a flat series doesn't divide by zero", () => {
  const out = buildSeriesPaths([7, 7, 7], 100, 50);
  for (const p of out.pts) assert.ok(Number.isFinite(p.x) && Number.isFinite(p.y));
});
