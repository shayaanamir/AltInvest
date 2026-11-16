// Tests for useAsync's request bookkeeping (audit G-24). Run: npm test.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createLatestRequest } from "./latestRequest.js";

test("a single normal request applies its result and is not silent", () => {
  const r = createLatestRequest();
  const a = r.start(false);
  assert.equal(a.silent, false);
  assert.equal(r.settle(a), true);
});

test("a silent refresh with nothing pending stays silent", () => {
  const r = createLatestRequest();
  r.settle(r.start(false));
  const s = r.start(true);
  assert.equal(s.silent, true);
  assert.equal(r.settle(s), true);
});

test("G-24: a silent refresh that supersedes a pending load takes the load over", () => {
  const r = createLatestRequest();
  const load = r.start(false);
  const refresh = r.start(true);
  assert.equal(refresh.silent, false, "promoted, so it clears loading when it settles");
  assert.equal(r.settle(load), false, "the superseded load is ignored");
  assert.equal(r.settle(refresh), true);
  // Once that settled, the next silent refresh is silent again.
  assert.equal(r.start(true).silent, true);
});

test("only the newest request applies", () => {
  const r = createLatestRequest();
  const a = r.start(false);
  const b = r.start(false);
  assert.equal(r.settle(a), false);
  assert.equal(r.settle(b), true);
});

test("a cancelled request (cleanup) does not apply and doesn't keep a load pending", () => {
  const r = createLatestRequest();
  const a = r.start(false);
  r.cancel(a);
  assert.equal(r.settle(a), false);
  assert.equal(r.start(true).silent, true);
});

test("cancelling an already superseded request leaves the newer one alone", () => {
  const r = createLatestRequest();
  const a = r.start(false);
  const b = r.start(true); // promoted
  r.cancel(a);
  assert.equal(r.settle(b), true);
});
