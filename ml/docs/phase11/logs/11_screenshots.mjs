// Headless Edge over the DevTools protocol: past-range screenshots for checkpoint 11 (D87-D89).
// Usage: node ml/docs/phase11/logs/11_screenshots.mjs <out dir> [frontend url] [backend url]
// Checkpoint 11 ran it against an isolated stack on the local Mongo: Vite on :5180 -> backend on :8010 (see checkpoint_11.md).
import { spawn } from "node:child_process";
import { writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const OUT = process.argv[2];
const FE = process.argv[3] || "http://localhost:5173";
const BE = process.argv[4] || "http://localhost:8000";
const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const PORT = 9334;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const profile = mkdtempSync(join(tmpdir(), "edge-shots-"));
const edge = spawn(EDGE, ["--headless=new", `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`,
  "--no-first-run", "--disable-gpu", "about:blank"], { stdio: "ignore" });

async function json(url, opts) {
  for (let i = 0; i < 40; i++) {
    try { const r = await fetch(url, opts); return await r.json(); } catch { await sleep(250); }
  }
  throw new Error(`no answer from ${url}`);
}

const targets = await json(`http://127.0.0.1:${PORT}/json/list`);
const page = targets.find((t) => t.type === "page");
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r));
let id = 0;
const pending = new Map();
ws.addEventListener("message", (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
});
const send = (method, params = {}) => new Promise((res, rej) => {
  const i = ++id;
  pending.set(i, (m) => (m.error ? rej(new Error(`${method}: ${m.error.message}`)) : res(m.result)));
  ws.send(JSON.stringify({ id: i, method, params }));
});
const evaluate = async (expr) => (await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true })).result.value;

async function viewport(w, h, mobile) {
  await send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: mobile ? 2 : 1, mobile });
}
async function go(path) {
  await send("Page.navigate", { url: FE + path });
  await sleep(1500);
}
async function waitFor(expr, ms = 90000) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    if (await evaluate(expr)) return true;
    await sleep(500);
  }
  throw new Error(`timeout waiting for ${expr}`);
}
async function shot(name, selector) {
  if (selector) await evaluate(`document.querySelector(${JSON.stringify(selector)})?.scrollIntoView({block: "center"}); true`);
  await sleep(800);
  const { data } = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(join(OUT, name), Buffer.from(data, "base64"));
}

await send("Page.enable");
await send("Runtime.enable");
const login = await (await fetch(`${BE}/auth/login`, { method: "POST", headers: { "content-type": "application/json" },
  body: JSON.stringify({ email: "demo@altinvest.com", password: "Demo1234!" }) })).json();
await go("/login");
await evaluate(`localStorage.setItem("altinvest_token", ${JSON.stringify(login.token)});
  localStorage.setItem("altinvest_user", ${JSON.stringify(JSON.stringify(login.user))}); true`);

const card = `document.querySelector(".adt-chart-card")`;
const ready = `document.querySelector(".adt-chart-card [data-layer='history']") !== null`;
const clickFilter = (f) => evaluate(`[...document.querySelectorAll(".adt-chart-card .sv2-segmented button")]
  .find((b) => b.innerText.trim() === ${JSON.stringify(f)})?.click(); true`);
const chartFacts = () => evaluate(`(() => {
  const c = ${card};
  const q = (s) => c.querySelector(s);
  return {
    theme: document.documentElement.getAttribute("data-theme"),
    filter: [...c.querySelectorAll(".sv2-segmented button")].find((b) => b.classList.contains("active"))?.innerText,
    toggle: q(".adt-past-toggle")?.innerText.trim() || null,
    toggle_checked: q(".adt-past-toggle input")?.checked ?? null,
    past_outer: q("[data-layer='past-outer']") !== null,
    past_inner: q("[data-layer='past-inner']") !== null,
    cone_outer: q("[data-layer='cone-outer']") !== null,
    legend: q(".adt-legend")?.innerText.replace(/\\s+/g, " ").trim() || null,
    past_caption: q("[data-role='past-caption']")?.innerText || null,
    calibration: q("[data-role='past-calibration']")?.innerText || null,
    page_width: document.documentElement.scrollWidth,
    ewma_on_page: /ewma/i.test(document.body.innerText),
  };
})()`);

const facts = {};
const ASSETS = ["BTC", "ETH", "SOL"];

// 1. desktop dark, 3M (91 days: the calibration line shows)
await viewport(1440, 1000, false);
for (const a of ASSETS) {
  await go(`/asset-detail?symbol=${a}`);
  await waitFor(ready);
  await clickFilter("3M");
  await sleep(500);
  facts[`${a}_desktop_dark_3M`] = await chartFacts();
  await shot(`11_${a.toLowerCase()}_desktop_dark.png`, ".adt-chart-card");
}

// 2. BTC extras (desktop dark): 1Y, 1M (31 days: no calibration line), toggle off
await go("/asset-detail?symbol=BTC");
await waitFor(ready);
await clickFilter("1Y");
await sleep(500);
facts.BTC_desktop_dark_1Y = await chartFacts();
await shot("11_btc_desktop_dark_1Y.png", ".adt-chart-card");
await clickFilter("1M");
await sleep(500);
facts.BTC_desktop_dark_1M = await chartFacts();
await shot("11_btc_desktop_dark_1M.png", ".adt-chart-card");
await clickFilter("3M");
await evaluate(`document.querySelector(".adt-past-toggle input").click(); true`);
await sleep(500);
facts.BTC_desktop_dark_3M_toggle_off = await chartFacts();
await shot("11_btc_desktop_dark_toggle_off.png", ".adt-chart-card");

// 3. phone dark, 3M
await viewport(390, 844, true);
for (const a of ASSETS) {
  await go(`/asset-detail?symbol=${a}`);
  await waitFor(ready);
  // The phone sidebar opens expanded (owner backlog item); collapsed by click, as in the 10.9 screenshots.
  facts[`${a}_phone_sidebar_collapsed_by_click`] = await evaluate(`(() => { const b = document.querySelector('[title="Collapse"]'); if (b) b.click(); return !!b; })()`);
  await sleep(800);
  await clickFilter("3M");
  await sleep(500);
  facts[`${a}_phone_dark_3M`] = await chartFacts();
  await shot(`11_${a.toLowerCase()}_phone_dark.png`, ".adt-chart-card");
}

// 4. desktop light, 3M (the theme is not persisted, so the top-bar toggle is clicked after each page load)
await viewport(1440, 1000, false);
for (const a of ASSETS) {
  await go(`/asset-detail?symbol=${a}`);
  await waitFor(ready);
  await evaluate(`document.querySelector('[aria-label="Toggle theme"]').click(); true`);
  await waitFor(`document.documentElement.getAttribute("data-theme") === "light"`);
  await clickFilter("3M");
  await sleep(500);
  facts[`${a}_desktop_light_3M`] = await chartFacts();
  await shot(`11_${a.toLowerCase()}_desktop_light.png`, ".adt-chart-card");
}

writeFileSync(join(OUT, "11_screenshot_facts.json"), JSON.stringify(facts, null, 2) + "\n");
console.log(JSON.stringify(facts, null, 2));
ws.close();
edge.kill();
process.exit(0);
