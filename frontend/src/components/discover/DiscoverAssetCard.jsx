import { useNavigate } from "react-router-dom";
import Sparkline from "./Sparkline";
import AssetAvatar from "../shared/AssetAvatar";

const SIGNAL_CLASS = { BUY: "signal-buy", HOLD: "signal-hold", SELL: "signal-sell" };
const SIGNAL_LABEL = { BUY: "Buy", HOLD: "Hold", SELL: "Sell" };

function aaiDotColor(score) {
  if (score >= 65) return "var(--sv2-green)";
  if (score >= 45) return "var(--sv2-accent)";
  return "var(--sv2-red)";
}

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

            <svg width="17" height="17" viewBox="0 0 24 24" fill={isWatching ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.8">
              <path d="M12 2.5l2.9 6.4 6.9.7-5.2 4.7 1.5 6.9L12 17.6l-6.1 3.6 1.5-6.9-5.2-4.7 6.9-.7z" />
            </svg>
          </button>
        </div>
      </div>

      <div className="disc-price-row">
        <span className="disc-price">
          ${item.price.toLocaleString(undefined, { maximumFractionDigits: item.price < 10 ? 4 : 2 })}
        </span>
        <span className={`disc-change ${positive ? "positive" : "negative"}`}>
          {positive ? "↗" : "↘"} {Math.abs(item.changePct).toFixed(2)}%
        </span>
      </div>
      <div className="disc-price-label">{item.type === "nft" ? "floor price" : "last price"}</div>

      <Sparkline data={item.sparkline} color={lineColor} />

      <div className="disc-card-bottom">
        <span className="disc-badge aai">
          <span className="disc-badge-dot" style={{ background: aaiDotColor(item.aaiScore) }} />
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