import { useNavigate } from "react-router-dom";
import Sparkline from "../charts/Sparkline";
import AssetAvatar from "../shared/AssetAvatar";
import { IconStar } from "../icons";
import { getAaiTierColor } from "../../utils/scoring";
import { formatAssetPrice } from "../../utils/formatters";

const SIGNAL_CLASS = { BUY: "signal-buy", HOLD: "signal-hold", SELL: "signal-sell" };
const SIGNAL_LABEL = { BUY: "Buy", HOLD: "Hold", SELL: "Sell" };

export default function DiscoverAssetCard({ item, isWatching, onToggleWatch, isComparing, onToggleCompare }) {
  const navigate = useNavigate();
  const positive = item.changePct >= 0;
  const lineColor = positive ? "var(--sv2-green)" : "var(--sv2-red)";

  return (
    <div
      className={`disc-card ${isComparing ? "in-compare" : ""}`}
      onClick={() => navigate(`/asset-detail?symbol=${item.symbol}`)}
      style={{ cursor: "pointer" }}
    >
      <div className="disc-card-top">
        <div className="disc-avatar-row">
          <AssetAvatar symbol={item.symbol} color={item.color} />
          <div className="disc-name-col">
            <div className="disc-name">{item.name}</div>
            <div className="disc-symbol">{item.symbol}</div>
          </div>
        </div>
        <div className="disc-card-actions">
          <button
            className={`disc-compare-btn ${isComparing ? "active" : ""}`}
            onClick={(e) => {
              e.stopPropagation();
              onToggleCompare(item);
            }}
          >
            Compare
          </button>
          <button
            className={`disc-star-btn ${isWatching ? "active" : ""}`}
            onClick={(e) => {
              e.stopPropagation();
              onToggleWatch(item);
            }}
            title="Add to watchlist"
          >
            <IconStar size={17} filled={isWatching} />
          </button>
        </div>
      </div>

      <div className="disc-price-row">
        <span className="disc-price">{formatAssetPrice(item.price)}</span>
        <span className={`disc-change ${positive ? "positive" : "negative"}`}>
          {positive ? "↗" : "↘"} {Math.abs(item.changePct).toFixed(2)}%
        </span>
      </div>
      <div className="disc-price-label">{item.type === "nft" ? "floor price" : "last price"}</div>

      <Sparkline data={item.sparkline} color={lineColor} />

      <div className="disc-card-bottom">
        <span className="disc-badge aai">
          <span className="disc-badge-dot" style={{ background: getAaiTierColor(item.aaiScore) }} />
          AAI {item.aaiScore}
        </span>
        {item.signal && (
          <span className={`disc-badge ${SIGNAL_CLASS[item.signal] || ""}`}>
            {SIGNAL_LABEL[item.signal] || item.signal}
          </span>
        )}
        {isWatching && <span className="disc-badge watching">👁 Watching</span>}
      </div>
    </div>
  );
}