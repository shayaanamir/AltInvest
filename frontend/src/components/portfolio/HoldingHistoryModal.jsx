import { useEffect, useState } from "react";
import { useAsync } from "../../hooks/useAsync";
import { portfolioApi } from "../../services/portfolioApi";
import { formatDate, useAppPreferences } from "../../services/appPreferences";
import { formatUsd } from "../../utils/formatters";
import { ErrorState, useToast } from "../../errors";
import "./addHoldingModal.css";

const TYPE_LABELS = { buy: "Buy", sell: "Sell", adjust: "Correction", remove: "Removed" };

function describe(t) {
  const qty = t.quantity != null ? `${t.quantity}` : "";
  if (t.type === "buy") {
    const price = t.price_usd != null ? ` at ${formatUsd(t.price_usd)}` : t.price_eth != null ? ` at ${t.price_eth} ETH` : "";
    return `${qty}${price}${t.note ? ` (${t.note})` : ""}`;
  }
  if (t.type === "sell") {
    const pnl = t.realised_pnl_usd != null ? ` · realised ${t.realised_pnl_usd >= 0 ? "+" : "-"}${formatUsd(Math.abs(t.realised_pnl_usd))}` : "";
    return `${qty} at ${formatUsd(t.price_usd)}${pnl}`;
  }
  if (t.type === "adjust") {
    if (t.note) return t.note;
    const changed = Object.keys(t.after || {}).filter((k) => k !== "cost_basis_usd");
    return changed.map((k) => `${k.replace(/_/g, " ")}: ${t.before?.[k] ?? "—"} → ${t.after[k] ?? "—"}`).join(", ");
  }
  return qty ? `${qty} removed` : "";
}

/**
 * A holding's history (GET /portfolio/holdings/{id}/transactions) and, for crypto, a form to record
 * a buy or sell. The server works out the new average price, cost basis and realised P&L.
 *   holding: { id, kind: "crypto" | "nft", name, symbol, quantity }
 */
export default function HoldingHistoryModal({ holding, onClose }) {
  useAppPreferences(); // dates follow the chosen format
  const toast = useToast();
  const isCrypto = holding.kind === "crypto";
  const { data: rows, error, refetch } = useAsync(() => portfolioApi.getTransactions(holding.id), [holding.id]);
  const [type, setType] = useState("buy");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && !saving && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose, saving]);

  const submit = async (e) => {
    e.preventDefault();
    const q = Number(quantity);
    const p = Number(price);
    const next = {};
    if (!quantity || !Number.isFinite(q) || q <= 0) next.quantity = "Enter a quantity greater than 0.";
    else if (type === "sell" && holding.quantity != null && q > holding.quantity) next.quantity = `You hold ${holding.quantity}.`;
    if (price === "" || !Number.isFinite(p) || p < 0) next.price = "Enter the price per unit in USD.";
    setErrors(next);
    if (Object.keys(next).length) return;

    setSaving(true);
    try {
      const res = await portfolioApi.recordTrade(holding.id, { type, quantity: q, price_usd: p });
      toast.success(
        res.closed ? `You sold all your ${holding.symbol}; the holding is closed.` : `${type === "buy" ? "Bought" : "Sold"} ${q} ${holding.symbol}.`,
        { title: "Transaction recorded" }
      );
      if (res.closed) return onClose();
      setQuantity("");
      setPrice("");
      refetch();
    } catch (err) {
      toast.error(err, { title: "Couldn't record that" });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="ahm-overlay" onClick={() => !saving && onClose()}>
      <div className="ahm" role="dialog" aria-modal="true" aria-label={`${holding.name} history`} onClick={(e) => e.stopPropagation()}>
        <div className="ahm-head">
          <h2>{holding.name} history</h2>
          <button type="button" className="ahm-close" aria-label="Close" onClick={onClose} disabled={saving}>×</button>
        </div>
        <p className="ahm-desc">
          Every buy, sell and correction for this holding. Cost basis uses the average buy price.
        </p>

        {isCrypto && (
          <form onSubmit={submit} noValidate>
            <div className="ahm-tabs" role="tablist">
              {["buy", "sell"].map((k) => (
                <button key={k} type="button" role="tab" aria-selected={type === k} className={type === k ? "active" : ""} onClick={() => setType(k)}>
                  Record a {k}
                </button>
              ))}
            </div>
            <div className="ahm-row">
              <div>
                <label className="ahm-label">Quantity</label>
                <input className="ahm-input" inputMode="decimal" value={quantity} onChange={(e) => setQuantity(e.target.value)} placeholder="e.g. 0.25" />
                {errors.quantity && <div className="ahm-field-error">{errors.quantity}</div>}
              </div>
              <div>
                <label className="ahm-label">Price per unit (USD)</label>
                <input className="ahm-input" inputMode="decimal" value={price} onChange={(e) => setPrice(e.target.value)} placeholder="e.g. 64000" />
                {errors.price && <div className="ahm-field-error">{errors.price}</div>}
              </div>
            </div>
            <div className="ahm-footer" style={{ marginTop: 14 }}>
              <button type="submit" className="ahm-submit" disabled={saving}>{saving ? "Saving…" : `Record ${type}`}</button>
            </div>
          </form>
        )}

        <label className="ahm-label">History</label>
        <div className="ahm-list" style={{ maxHeight: 260 }}>
          {error ? (
            <ErrorState error={error} onRetry={refetch} title="Couldn't load the history" />
          ) : !rows ? (
            <div className="ahm-empty">Loading…</div>
          ) : rows.length === 0 ? (
            <div className="ahm-empty">Nothing recorded yet. Changes made from now on appear here.</div>
          ) : (
            rows.map((t) => (
              <div key={t.id} className="ahm-item" style={{ cursor: "default" }}>
                <span className="ahm-item-main">
                  <span className="ahm-item-name">{TYPE_LABELS[t.type] || t.type}</span>
                  <span className="ahm-item-sub">{describe(t)}</span>
                </span>
                <span className="ahm-item-price">{formatDate(t.timestamp)}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
