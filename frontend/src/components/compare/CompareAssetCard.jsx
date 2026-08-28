import { formatAssetPrice, formatPct } from "../../utils/formatters";

export default function CompareAssetCard({ asset, onRemove }) {
  const positive = asset.change24h >= 0;

  return (
    <div className="cmp-card cmp-asset-card">
      <div className="cmp-asset-card-top">
        <div className="cmp-asset-card-id">
          <div className="cmp-avatar" style={{ background: asset.avatarColor }}>
            {asset.symbol.slice(0, 3)}
          </div>
          <div>
            <div className="cmp-asset-card-name">{asset.name}</div>
            <div className="cmp-asset-card-sub">{asset.subtitle}</div>
          </div>
        </div>
        <button className="cmp-icon-btn" onClick={() => onRemove(asset.id)} aria-label="Remove">
          ×
        </button>
      </div>

      <div className="cmp-asset-card-price">
        {asset.priceLabel || formatAssetPrice(asset.price)}
      </div>

      <div className="cmp-badge-row">
        <span className={`cmp-badge ${positive ? "positive" : "negative"}`}>
          {positive ? "↗" : "↘"} {formatPct(asset.change24h, { withSign: true })}
        </span>
        {asset.aaiScore != null && (
          <span className="cmp-badge neutral">● AAI {Math.round(asset.aaiScore)}</span>
        )}
        {asset.watching && <span className="cmp-badge neutral">◎ Watching</span>}
        {asset.held && <span className="cmp-badge neutral">◆ Held</span>}
      </div>
    </div>
  );
}