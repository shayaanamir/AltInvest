import { formatAssetPrice } from "../../../utils/formatters";
import { getAaiTierColor } from "../../../utils/scoring";

/** One search row: an asset / collection (price, AAI, held / watching), an insight, or a recent search. */
export default function SearchResultItem({ id, item, priceKey, active, onHover, onSelect }) {
  const price = priceKey ? item[priceKey] : null;
  const isMarket = item.kind === "asset" || item.kind === "collection";

  return (
    <button
      type="button"
      id={id}
      role="option"
      aria-selected={!!active}
      className={`tb-search-item ${active ? "active" : ""}`}
      onMouseEnter={onHover}
      onClick={() => onSelect(item)}
    >
      <div className="tb-search-item-text">
        <div className="tb-search-item-name">
          {item.name}
          {isMarket && item.symbol && <span className="tb-search-item-symbol"> · {item.symbol}</span>}
        </div>
        {(isMarket || item.subtitle) && (
          <div className="tb-search-item-sub">
            {isMarket && (price != null ? formatAssetPrice(price) : "No price")}
            {item.subtitle ? `${isMarket ? " · " : ""}${item.subtitle}` : ""}
          </div>
        )}
      </div>

      {isMarket && (
        <div className="tb-search-item-meta">
          {item.held && <span className="tb-search-tag held">Held</span>}
          {!item.held && item.watching && <span className="tb-search-tag watching">Watching</span>}
          {item.aaiScore != null && (
            <span className="tb-search-tag aai">
              <span className="tb-search-tag-dot" style={{ background: getAaiTierColor(item.aaiScore) }} />
              AAI {Math.round(item.aaiScore)}
            </span>
          )}
        </div>
      )}
      {item.kind === "insight" && item.url && <span className="tb-search-tag">Opens source ↗</span>}
    </button>
  );
}
