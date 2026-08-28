import AssetAvatar from "../shared/AssetAvatar";

const SIGNAL_CLASS = { BUY: "signal-buy", HOLD: "signal-hold", SELL: "signal-sell" };
const SIGNAL_LABEL = { BUY: "Buy", HOLD: "Hold", SELL: "Sell" };

function aaiDotColor(score) {
  if (score == null) return "var(--sv2-text-mute)";
  if (score >= 65) return "var(--sv2-green)";
  if (score >= 45) return "var(--sv2-accent)";
  return "var(--sv2-red)";
}

export default function WatchlistRow({ item, onAddToPortfolio, onRemove }) {
  const positive = (item.changePct ?? 0) >= 0;

  return (
    <div className="wl-row">
      <div className="wl-asset">
        <AssetAvatar symbol={item.symbol} color={item.color} size={36} />
        <div>
          <div className="wl-asset-name">{item.name}</div>
          <div className="wl-asset-sub">{item.subcategory}</div>
        </div>
      </div>

      <div className="wl-price">
        {item.price != null
          ? `$${item.price.toLocaleString(undefined, { maximumFractionDigits: item.price < 10 ? 4 : 2 })}`
          : "—"}
      </div>

      <span className={`wl-change ${positive ? "positive" : "negative"}`}>
        {positive ? "↗" : "↘"} {Math.abs(item.changePct ?? 0).toFixed(2)}%
      </span>

      <div className="wl-badges">
        {item.aaiScore != null && (
          <span className="wl-badge aai">
            <span className="wl-badge-dot" style={{ background: aaiDotColor(item.aaiScore) }} />
            AAI {item.aaiScore}
          </span>
        )}
        {item.signal && <span className={`wl-badge ${SIGNAL_CLASS[item.signal] || ""}`}>{SIGNAL_LABEL[item.signal] || item.signal}</span>}
      </div>

      <div className="wl-actions">
        <button className="wl-add-btn" onClick={() => onAddToPortfolio(item)}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 6L9 17l-5-5" /></svg>
          Add to portfolio
        </button>
        <button className="wl-icon-btn" title="Set alert">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path d="M18 8a6 6 0 10-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.7 21a2 2 0 01-3.4 0" />
          </svg>
        </button>
        <button className="wl-icon-btn danger" onClick={() => onRemove(item)} title="Remove">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M18 6L6 18M6 6l12 12" /></svg>
        </button>
      </div>
    </div>
  );
}