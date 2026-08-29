import AssetAvatar from "../shared/AssetAvatar";
import { IconBell, IconTrash } from "../icons";
import { getAaiTierColor } from "../../utils/scoring";
import { formatAssetPrice } from "../../utils/formatters";

const SIGNAL_CLASS = { BUY: "signal-buy", HOLD: "signal-hold", SELL: "signal-sell" };
const SIGNAL_LABEL = { BUY: "Buy", HOLD: "Hold", SELL: "Sell" };

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
        {item.price != null ? formatAssetPrice(item.price) : "—"}
      </div>

      <span className={`wl-change ${positive ? "positive" : "negative"}`}>
        {positive ? "↗" : "↘"} {Math.abs(item.changePct ?? 0).toFixed(2)}%
      </span>

      <div className="wl-badges">
        {item.aaiScore != null && (
          <span className="wl-badge aai">
            <span className="wl-badge-dot" style={{ background: getAaiTierColor(item.aaiScore) }} />
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
          <IconBell size={15} />
        </button>
        <button className="wl-icon-btn danger" onClick={() => onRemove(item)} title="Remove">
          <IconTrash size={15} />
        </button>
      </div>
    </div>
  );
}