import { useState } from "react";
import { IconTrash, IconDownload } from "../icons";
import { portfolioApi } from "../../services/portfolioApi";
import { watchlistApi } from "../../services/watchlistApi";
import { alertsApi } from "../../services/alertsApi";
import { useToast } from "../../errors";

// Quote a CSV cell when it holds a comma, quote or newline. Text starting with = + - @ would be run as
// a formula by spreadsheets, so those get a leading apostrophe (numbers are left alone).
const cell = (v) => {
  let s = String(v ?? "");
  if (typeof v === "string" && /^[=+\-@\t\r]/.test(s)) s = `'${s}`;
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

// One section per kind of data, each with its own header row, separated by a blank line.
function section(title, columns, records) {
  const lines = [cell(title), columns.map(([label]) => cell(label)).join(",")];
  records.forEach((r) => lines.push(columns.map(([, get]) => cell(get(r))).join(",")));
  return lines.join("\n");
}

function toCsv({ cryptoHoldings, nftHoldings, watchlists, alerts }) {
  const watchlistItems = watchlists.flatMap((l) => l.items.map((i) => ({ list: l.name, item: i })));
  return [
    section("Crypto holdings", [
      ["Symbol", (h) => h.symbol],
      ["Name", (h) => h.name],
      ["Quantity", (h) => h.quantity],
      ["Avg buy price (USD)", (h) => h.avgBuyPriceUsd],
      ["Cost basis (USD)", (h) => h.costBasisUsd],
      ["Current value (USD)", (h) => h.valueUsd],
      ["Date added", (h) => h.dateAdded],
    ], cryptoHoldings),
    section("NFT holdings", [
      ["Collection", (h) => h.collectionName],
      ["Slug", (h) => h.collectionSlug],
      ["Token ID", (h) => h.tokenId],
      ["Quantity", (h) => h.quantity],
      ["Avg buy price (ETH)", (h) => h.avgBuyPriceEth],
      ["ETH/USD at buy", (h) => h.ethUsdRateAtBuy],
      ["Cost basis (USD)", (h) => h.costBasisUsd],
      ["Current value (USD)", (h) => h.valueUsd],
      ["Date added", (h) => h.dateAdded],
    ], nftHoldings),
    section("Watchlists", [
      ["Watchlist", (r) => r.list],
      ["Type", (r) => r.item.type],
      ["Asset", (r) => r.item.name || r.item.symbol || r.item.id],
      ["ID", (r) => r.item.id],
    ], watchlistItems),
    section("Alerts", [
      ["Target", (a) => a.targetName || a.targetSymbol || a.targetSlug],
      ["Target type", (a) => a.targetType],
      ["Metric", (a) => a.metricType],
      ["Condition", (a) => a.condition],
      ["Threshold", (a) => a.thresholdValue],
      ["Status", (a) => a.status],
      ["Channel", (a) => a.deliveryChannel],
      ["Created", (a) => a.createdAt],
      ["Last triggered", (a) => a.lastTriggeredAt],
    ], alerts),
  ].join("\n\n");
}

export default function DataAccountSection({ data }) {
  const [confirming, setConfirming] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [exporting, setExporting] = useState(false);
  const toast = useToast();

  if (!data) return null;

  // Exports what is actually stored for this account, fetched at click time.
  const handleExport = async (format) => {
    setExporting(true);
    let payload;
    try {
      const [cryptoHoldings, nftHoldings, watchlists, alerts] = await Promise.all([
        portfolioApi.getCryptoHoldings(),
        portfolioApi.getNftHoldings(),
        watchlistApi.getInitialListsAsync(),
        alertsApi.getAlerts(),
      ]);
      payload = { cryptoHoldings, nftHoldings, watchlists, alerts };
    } catch (e) {
      toast.error(e, { title: "Couldn't export your data" });
      return;
    } finally {
      setExporting(false);
    }
    const content = format === "JSON" ? JSON.stringify(payload, null, 2) : toCsv(payload);
    const blob = new Blob([content], { type: format === "JSON" ? "application/json" : "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `altinvest-export.${format.toLowerCase()}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const requiredPhrase = data.accountDeletion?.confirmationPhrase || "DELETE";
  const canDelete = confirmText.trim() === requiredPhrase;

  return (
    <>
      <div className="sv2-card set-subcard">
        <div className="set-section-title">Export your data</div>
        <div className="set-row-desc set-mb-16">Holdings, watchlists and alerts</div>
        <div className="set-export-row">
          {(data.exportFormats || []).map((fmt) => (
            <button key={fmt} className="sv2-btn-outline set-export-btn" disabled={exporting} onClick={() => handleExport(fmt)}>
              <IconDownload size={14} /> Export {fmt}
            </button>
          ))}
        </div>
      </div>


      <div className="sv2-card set-subcard">
        <div className="set-section-title" style={{ color: "var(--sv2-red)" }}>Delete account</div>
        <div className="set-row-desc set-mb-16">Permanent — requires a typed confirmation</div>

        {!confirming ? (
          <button className="set-btn-danger" onClick={() => setConfirming(true)}>
            <IconTrash size={14} /> Delete account
        </button>
        ) : (
          <div className="set-delete-confirm">
            <p className="set-row-desc">Type <strong>{requiredPhrase}</strong> to confirm.</p>
            <input
              className="set-input"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder={requiredPhrase}
            />
            <div className="set-delete-actions">
              <button className="set-btn-danger" disabled={!canDelete}>Confirm delete</button>
              <button className="sv2-btn-outline" style={{ width: "auto" }} onClick={() => { setConfirming(false); setConfirmText(""); }}>
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}