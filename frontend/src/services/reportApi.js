import { dashboardApi } from "./dashboardApi";
import { loadPortfolioAnalysis } from "./analysisApi";
import { formatCurrencyFull, formatCurrencyCompact, formatAssetPrice, formatPct } from "../utils/formatters";

const esc = (v) =>
  String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const STYLE = `
  body{font:14px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif;color:#1c1c24;max-width:820px;margin:32px auto;padding:0 20px}
  h1{font-size:24px;margin:0 0 4px} h2{font-size:16px;margin:28px 0 8px;border-bottom:1px solid #ddd;padding-bottom:4px}
  .sub{color:#6b6b7b;margin:0 0 8px} table{width:100%;border-collapse:collapse} th,td{text-align:left;padding:6px 8px;border-bottom:1px solid #eee}
  th{font-size:12px;color:#6b6b7b;text-transform:uppercase;letter-spacing:.04em} td.n,th.n{text-align:right}
  .note{font-size:12px;color:#6b6b7b;margin-top:28px} li{margin:4px 0} a{color:#b4502d}
  @media print{body{margin:0}}`;

const table = (head, rows) =>
  `<table><thead><tr>${head.map((h, i) => `<th${i ? ' class="n"' : ""}>${esc(h)}</th>`).join("")}</tr></thead><tbody>${rows
    .map((r) => `<tr>${r.map((c, i) => `<td${i ? ' class="n"' : ""}>${esc(c)}</td>`).join("")}</tr>`)
    .join("")}</tbody></table>`;

/** Builds a self-contained HTML report from the signed-in user's stored data. */
export async function buildReportHtml() {
  const [analysis, stats, trending, insights, user] = await Promise.all([
    loadPortfolioAnalysis(),
    dashboardApi.getMarketStats(),
    dashboardApi.getTrendingAssets(),
    dashboardApi.getMarketInsights(),
    dashboardApi.getCurrentUser().catch(() => null),
  ]);

  const now = new Date();
  const a = analysis;
  const sections = [];

  // Portfolio
  if (a.empty) {
    sections.push(`<h2>Your portfolio</h2><p>No holdings recorded yet.</p>`);
  } else {
    const highlights = [];
    if (a.largest) highlights.push(`${a.largest.label} is ${a.largest.sharePct.toFixed(0)}% of the portfolio${a.concentrated ? " (heavily concentrated)" : ""}.`);
    if (a.strongest) highlights.push(`Highest AAI score: ${a.strongest.label} (${Math.round(a.strongest.aaiScore)}).`);
    if (a.weakest) highlights.push(`Lowest AAI score: ${a.weakest.label} (${Math.round(a.weakest.aaiScore)}).`);
    if (a.toReduce.length) highlights.push(`Current signal suggests reducing: ${a.toReduce.map((p) => p.label).join(", ")}.`);
    if (a.unscored.length) highlights.push(`No stored score for ${a.unscored.map((p) => p.label).join(", ")}.`);

    sections.push(`<h2>Your portfolio</h2>
      <p>Total value <strong>${esc(formatCurrencyFull(a.totalValue))}</strong> across ${a.positions.length} position${a.positions.length === 1 ? "" : "s"};
      unrealised P&amp;L ${esc(formatCurrencyFull(a.summary.totalProfitLoss))} (${esc(formatPct(a.summary.totalProfitLossPct, { withSign: true }))}).
      ${a.weightedAai != null ? `Value-weighted AAI score ${Math.round(a.weightedAai)}.` : ""}
      ${a.intel.aggregateRiskScore != null ? `Average risk score ${a.intel.aggregateRiskScore}/100 (higher means lower risk).` : ""}</p>
      ${table(
        ["Holding", "Value", "Share", "AAI", "Signal"],
        a.positions.map((p) => [p.label, formatCurrencyFull(p.valueUsd), `${p.sharePct.toFixed(1)}%`, p.aaiScore != null ? Math.round(p.aaiScore) : "—", p.action])
      )}
      ${highlights.length ? `<h2>What stands out</h2><ul>${highlights.map((h) => `<li>${esc(h)}</li>`).join("")}</ul>` : ""}`);
  }

  // Market
  sections.push(`<h2>Market snapshot</h2>
    <p>24h volume across tracked assets: <strong>${esc(formatCurrencyCompact(stats.totalVolume24h))}</strong>.
    Overall sentiment <strong>${esc(stats.marketMood)}</strong> (${esc(stats.globalSentiment)}/100)${stats.marketMoodConfidence != null ? `, ${esc(stats.marketMoodConfidence)}% confidence` : ""}.</p>`);

  if (trending.length) {
    sections.push(`<h2>Biggest movers</h2>${table(
      ["Asset", "Price", "24h", "AAI"],
      trending.map((t) => [`${t.name} (${t.symbol})`, formatAssetPrice(t.price), formatPct(t.change24h, { withSign: true }), t.aai?.score != null ? Math.round(t.aai.score) : "—"])
    )}`);
  }

  if (insights.length) {
    sections.push(`<h2>Market insights</h2><ul>${insights
      .map(
        (i) =>
          `<li><strong>${esc(i.title)}</strong> — ${esc(i.source)}, ${esc((i.publishedAt || "").slice(0, 10))} (${esc(i.impact)})${
            i.url ? ` · <a href="${esc(i.url)}">source</a>` : ""
          }</li>`
      )
      .join("")}</ul>`);
  }

  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>AltInvest report ${esc(now.toISOString().slice(0, 10))}</title><style>${STYLE}</style></head><body>
    <h1>AltInvest report</h1>
    <p class="sub">${user?.name ? `Prepared for ${esc(user.name)} · ` : ""}${esc(now.toLocaleString())}</p>
    ${sections.join("\n")}
    <p class="note">Generated from the data stored for your account and the platform's scores at the time shown. It describes current positions and is not a forecast or financial advice.</p>
  </body></html>`;
}

/** Builds the report and saves it as an .html file the browser can open or print to PDF. */
export async function downloadReport() {
  const html = await buildReportHtml();
  const url = URL.createObjectURL(new Blob([html], { type: "text/html" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `altinvest-report-${new Date().toISOString().slice(0, 10)}.html`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
