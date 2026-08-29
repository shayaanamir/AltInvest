import { useState } from "react";
import portfolioData from "../../data/sample_data/portfolio.json";
import watchlistsData from "../../data/sample_data/watchlists.json";
import alertsData from "../../data/sample_data/alerts.json";
import { IconTrash, IconDownload } from "../icons";

function toCsv(payload) {
  const rows = ["type,name,value"];
  (payload.holdings.cryptoHoldings || []).forEach((h) => rows.push(`crypto,${h.symbol},${h.valueUsd}`));
  (payload.holdings.nftHoldings || []).forEach((h) => rows.push(`nft,${h.collectionName},${h.valueUsd}`));
  (payload.watchlists.lists || []).forEach((l) => rows.push(`watchlist,${l.name},${l.items.length}`));
  (payload.alerts.alerts || []).forEach((a) => rows.push(`alert,${a.targetName || a.targetSymbol || a.targetSlug},${a.status}`));
  return rows.join("\n");
}

export default function DataAccountSection({ data }) {
  const [confirming, setConfirming] = useState(false);
  const [confirmText, setConfirmText] = useState("");

  if (!data) return null;

  const handleExport = (format) => {
    const payload = { holdings: portfolioData, watchlists: watchlistsData, alerts: alertsData };
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
            <button key={fmt} className="sv2-btn-outline set-export-btn" onClick={() => handleExport(fmt)}>
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