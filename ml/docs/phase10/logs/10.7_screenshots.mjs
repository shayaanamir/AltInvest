// Headless Edge over the DevTools protocol: item card + demo holdings screenshots for checkpoint 10.7.
import { spawn } from "node:child_process";
import { writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const OUT = process.argv[2];
const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const FE = "http://localhost:5173";
const PORT = 9333;
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
  await sleep(700);
  const { data } = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(join(OUT, name), Buffer.from(data, "base64"));
}

await send("Page.enable");
await send("Runtime.enable");
const login = await (await fetch("http://localhost:8000/auth/login", { method: "POST", headers: { "content-type": "application/json" },
  body: JSON.stringify({ email: "demo@altinvest.com", password: "Demo1234!" }) })).json();
await go("/login");
await evaluate(`localStorage.setItem("altinvest_token", ${JSON.stringify(login.token)});
  localStorage.setItem("altinvest_user", ${JSON.stringify(JSON.stringify(login.user))}); true`);

const facts = {};
const cardText = `document.querySelector(".nft-item-card")?.innerText || ""`;
const ready = `document.querySelector(".nft-item-accuracy") !== null`;

// 1. desktop dark: pudgypenguins #7862 (demo holding)
await viewport(1440, 1000, false);
await go("/nft-collection?slug=pudgypenguins&token=7862");
await waitFor(ready);
facts.desktop_theme = await evaluate(`document.documentElement.getAttribute("data-theme")`);
facts.card_text_pudgy = await evaluate(cardText);
await shot("10.7_item_card_desktop_dark.png", ".nft-item-card");

// 2. desktop light (top-bar toggle)
await evaluate(`document.querySelector('[aria-label="Toggle theme"]').click(); true`);
await sleep(800);
facts.desktop_theme_after_toggle = await evaluate(`document.documentElement.getAttribute("data-theme")`);
await shot("10.7_item_card_desktop_light.png", ".nft-item-card");

// 3. phone dark (new load, default dark)
await viewport(390, 844, true);
await go("/nft-collection?slug=pudgypenguins&token=7862");
await waitFor(ready);
facts.phone_sidebar_collapsed_by_click = await evaluate(`(() => { const b = document.querySelector('[title="Collapse"]'); if (b) b.click(); return !!b; })()`);
await sleep(800);
facts.phone_theme = await evaluate(`document.documentElement.getAttribute("data-theme")`);
facts.phone_page_scroll_width = await evaluate(`document.documentElement.scrollWidth`);
await shot("10.7_item_card_phone_dark.png", ".nft-item-card");

// 4. azuki #8604 (the second demo holding), desktop dark
await viewport(1440, 1000, false);
await go("/nft-collection?slug=azuki&token=8604");
await waitFor(ready);
facts.card_text_azuki = await evaluate(cardText);
await shot("10.7_item_card_azuki_desktop_dark.png", ".nft-item-card");

// 5. demo holdings (portfolio), desktop dark
await go("/portfolio");
await waitFor(`document.querySelectorAll(".pv2-nft-est").length >= 2`);
facts.holdings_text = await evaluate(`[...document.querySelectorAll(".pv2-nft-card")].map((c) => c.innerText)`);
await shot("10.7_demo_holdings_desktop_dark.png", ".pv2-nft-grid");

const all = [facts.card_text_pudgy, facts.card_text_azuki].join("\n");
facts.caption_present = all.includes("An estimate of what this item might sell for now, mostly driven by the collection floor and recent sales. Not a price prediction.");
facts.accuracy_line_present = all.includes("Typical error: Accuracy check pending");
facts.no_range_or_drivers = !/range|driver|lower|upper/i.test(all);
facts.no_usd_on_card = !/\$|USD/.test(all);
writeFileSync(join(OUT, "10.7_screenshot_facts.json"), JSON.stringify(facts, null, 1));
console.log(JSON.stringify(facts, null, 1));
ws.close();
edge.kill();
process.exit(0);
