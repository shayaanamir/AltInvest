import { useState } from "react";
import portfolioData from "../../data/sample_data/portfolio.json";
import watchlistsData from "../../data/sample_data/watchlists.json";
import alertsData from "../../data/sample_data/alerts.json";

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
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" class="bi bi-download" viewBox="0 0 16 16">
                <path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5"/>
                <path d="M7.646 11.854a.5.5 0 0 0 .708 0l3-3a.5.5 0 0 0-.708-.708L8.5 10.293V1.5a.5.5 0 0 0-1 0v8.793L5.354 8.146a.5.5 0 1 0-.708.708z"/>
            </svg> Export {fmt}
            </button>
          ))}
        </div>
      </div>

      <div className="sv2-card set-subcard">
        <div className="set-section-title" style={{ color: "var(--sv2-red)" }}>Delete account</div>
        <div className="set-row-desc set-mb-16">Permanent — requires a typed confirmation</div>

        {!confirming ? (
          <button className="set-btn-danger" onClick={() => setConfirming(true)}>
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" class="bi bi-trash3" viewBox="0 0 16 16">
            <path d="M6.5 1h3a.5.5 0 0 1 .5.5v1H6v-1a.5.5 0 0 1 .5-.5M11 2.5v-1A1.5 1.5 0 0 0 9.5 0h-3A1.5 1.5 0 0 0 5 1.5v1H1.5a.5.5 0 0 0 0 1h.538l.853 10.66A2 2 0 0 0 4.885 16h6.23a2 2 0 0 0 1.994-1.84l.853-10.66h.538a.5.5 0 0 0 0-1zm1.958 1-.846 10.58a1 1 0 0 1-.997.92h-6.23a1 1 0 0 1-.997-.92L3.042 3.5zm-7.487 1a.5.5 0 0 1 .528.47l.5 8.5a.5.5 0 0 1-.998.06L5 5.03a.5.5 0 0 1 .47-.53Zm5.058 0a.5.5 0 0 1 .47.53l-.5 8.5a.5.5 0 1 1-.998-.06l.5-8.5a.5.5 0 0 1 .528-.47M8 4.5a.5.5 0 0 1 .5.5v8.5a.5.5 0 0 1-1 0V5a.5.5 0 0 1 .5-.5"/>
            </svg> Delete account
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