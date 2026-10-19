import { useEffect, useMemo, useState } from "react";
import { useAsync } from "../../hooks/useAsync";
import { fetchUniverse } from "../../services/assetRepository";
import { portfolioApi } from "../../services/portfolioApi";
import { formatAssetPrice } from "../../utils/formatters";
import { ErrorState, useToast } from "../../errors";
import "./addHoldingModal.css";

const KINDS = [
  { key: "crypto", label: "Crypto" },
  { key: "nft", label: "NFT" },
];

/**
 * Adds a holding to the signed-in user's portfolio (POST /portfolio/holdings).
 * Assets come from the covered universe (GET /discover), so only assets the platform scores can be picked.
 * Closes itself and calls onAdded() on success; failures stay in the dialog as a toast so nothing typed is lost.
 */
export default function AddHoldingModal({ onClose, onAdded, initialKind = "crypto" }) {
  const toast = useToast();
  const { data: universe, loading, error, refetch } = useAsync(() => fetchUniverse({ category: "all", sort: "name", order: "asc" }), []);

  const [kind, setKind] = useState(initialKind);
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [tokenId, setTokenId] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && !submitting && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose, submitting]);

  const choices = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (universe || [])
      .filter((u) => u.type === kind)
      .filter((u) => !q || u.name.toLowerCase().includes(q) || (u.symbol || "").toLowerCase().includes(q));
  }, [universe, kind, query]);

  const selected = (universe || []).find((u) => u.id === selectedId && u.type === kind) || null;
  const ethUsd = (universe || []).find((u) => u.type === "crypto" && u.symbol === "ETH")?.price ?? null;
  const isNft = kind === "nft";

  const switchKind = (next) => {
    setKind(next);
    setSelectedId(null);
    setPrice("");
    setFieldErrors({});
  };

  const pick = (item) => {
    setSelectedId(item.id);
    setFieldErrors((e) => ({ ...e, asset: undefined }));
  };

  const validate = () => {
    const errors = {};
    if (!selected) errors.asset = isNft ? "Choose a collection." : "Choose an asset.";
    if (isNft) {
      if (!tokenId.trim()) errors.tokenId = "Enter the token ID you own.";
    } else {
      const qty = Number(quantity);
      if (!quantity || !Number.isFinite(qty) || qty <= 0) errors.quantity = "Enter a quantity greater than 0.";
    }
    const p = Number(price);
    if (price === "" || !Number.isFinite(p) || p <= 0) {
      errors.price = isNft ? "Enter the price you paid, in ETH." : "Enter your average buy price in USD.";
    }
    return errors;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const errors = validate();
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    const p = Number(price);
    const payload = isNft
      ? {
          asset_type: "nft",
          nft_collection_slug: selected.id,
          nft_token_id: tokenId.trim(),
          quantity: 1,
          avg_buy_price_eth: p,
          ...(ethUsd ? { avg_buy_eth_usd_rate: ethUsd, cost_basis_usd: Math.round(p * ethUsd * 100) / 100 } : {}),
        }
      : {
          asset_type: "crypto",
          symbol: selected.symbol,
          quantity: Number(quantity),
          avg_buy_price_usd: p,
          cost_basis_usd: Math.round(Number(quantity) * p * 100) / 100,
        };

    setSubmitting(true);
    try {
      await portfolioApi.addHolding(payload);
    } catch (err) {
      toast.error(err, { title: "Couldn't add the holding" });
      setSubmitting(false);
      return;
    }
    onAdded?.();
    onClose();
  };

  return (
    <div className="ahm-overlay" onClick={() => !submitting && onClose()}>
      <form
        className="ahm"
        role="dialog"
        aria-modal="true"
        aria-label="Add a holding"
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSubmit}
        noValidate
      >
        <div className="ahm-head">
          <h2>Add a holding</h2>
          <button type="button" className="ahm-close" aria-label="Close" onClick={onClose} disabled={submitting}>×</button>
        </div>
        <p className="ahm-desc">Record something you own. It feeds your portfolio value, performance and every score shown against your holdings.</p>

        <div className="ahm-tabs" role="tablist">
          {KINDS.map((k) => (
            <button
              key={k.key}
              type="button"
              role="tab"
              aria-selected={kind === k.key}
              className={kind === k.key ? "active" : ""}
              onClick={() => switchKind(k.key)}
            >
              {k.label}
            </button>
          ))}
        </div>

        <label className="ahm-label">{isNft ? "Collection" : "Asset"}</label>
        <input
          className="ahm-input"
          placeholder={isNft ? "Search collections" : "Search assets"}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus
        />
        <div className="ahm-list">
          {error ? (
            <ErrorState error={error} onRetry={refetch} title="Couldn't load the asset list" />
          ) : loading ? (
            <div className="ahm-empty">Loading…</div>
          ) : choices.length === 0 ? (
            <div className="ahm-empty">{query ? "No matches." : "Nothing covered in this category yet."}</div>
          ) : (
            choices.map((c) => (
              <button
                key={c.id}
                type="button"
                className={`ahm-item ${c.id === selectedId ? "selected" : ""}`}
                onClick={() => pick(c)}
              >
                <span className="ahm-dot" style={{ background: c.color || "var(--sv2-accent)" }}>
                  {(c.symbol || c.name).slice(0, 3).toUpperCase()}
                </span>
                <span className="ahm-item-main">
                  <span className="ahm-item-name">{c.name}</span>
                  <span className="ahm-item-sub">{c.subcategory}</span>
                </span>
                <span className="ahm-item-price">{c.priceLabel || formatAssetPrice(c.price)}</span>
              </button>
            ))
          )}
        </div>
        {fieldErrors.asset && <div className="ahm-field-error">{fieldErrors.asset}</div>}

        {isNft ? (
          <>
            <label className="ahm-label">Token ID</label>
            <input className="ahm-input" inputMode="numeric" placeholder="e.g. 4271" value={tokenId} onChange={(e) => setTokenId(e.target.value)} />
            {fieldErrors.tokenId && <div className="ahm-field-error">{fieldErrors.tokenId}</div>}
          </>
        ) : (
          <>
            <label className="ahm-label">Quantity</label>
            <input className="ahm-input" inputMode="decimal" placeholder="e.g. 0.5" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
            {fieldErrors.quantity && <div className="ahm-field-error">{fieldErrors.quantity}</div>}
          </>
        )}

        <label className="ahm-label">{isNft ? "Price paid (ETH)" : "Average buy price (USD)"}</label>
        <input
          className="ahm-input"
          inputMode="decimal"
          placeholder={selected && !isNft ? `Now ${formatAssetPrice(selected.price)}` : "e.g. 2500"}
          value={price}
          onChange={(e) => setPrice(e.target.value)}
        />
        {fieldErrors.price && <div className="ahm-field-error">{fieldErrors.price}</div>}
        {isNft && !ethUsd && (
          <div className="ahm-hint">No ETH price is stored, so the USD cost basis can't be worked out for this NFT.</div>
        )}

        <div className="ahm-footer">
          <button type="button" className="ahm-cancel" onClick={onClose} disabled={submitting}>Cancel</button>
          <button type="submit" className="ahm-submit" disabled={submitting}>{submitting ? "Adding…" : "Add holding"}</button>
        </div>
      </form>
    </div>
  );
}
