import { formatAssetPrice } from "../../../utils/formatters";
import { getAaiTierColor } from "../../../utils/scoring";

export default function SearchResultItem({ item, priceKey, onSelect }) {
  const price = item[priceKey];

  return (
    <button type="button" className="tb-search-item" onClick={() => onSelect(item)}>
      <div className="tb-search-item-text">
        <div className="tb-search-item-name">
          {item.name} <span className="tb-search-item-symbol">· {item.symbol}</span>
        </div>
        <div className="tb-search-item-sub">
          {price != null ? formatAssetPrice(price) : "—"}
          {item.subtitle ? ` · ${item.subtitle}` : ""}
        </div>
      </div>

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
    </button>
  );
}