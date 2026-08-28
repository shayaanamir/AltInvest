import { useNavigate } from "react-router-dom";
import AssetAvatar from "../shared/AssetAvatar";
import MiniChart from "../charts/MiniChart";
import { formatAssetPrice, formatPct } from "../../utils/formatters";
import { IconStar } from "../icons";

const SIGNAL_CLASS = { BUY: "positive", HOLD: "neutral", SELL: "negative" };
const SIGNAL_LABEL = { BUY: "Buy", HOLD: "Hold", SELL: "Sell" };

export default function SimilarAssetCard({ asset }) {
  const navigate = useNavigate();
  const positive = asset.change24h >= 0;

  return (
    <div className="sv2-card adt-similar-card" onClick={() => navigate(`/asset-detail?symbol=${asset.symbol}`)}>
      <div className="adt-similar-top">
        <div className="adt-similar-id">
          <AssetAvatar symbol={asset.symbol} color={asset.logoColor} size={30} />
          <div>
            <div className="adt-similar-name">{asset.name}</div>
            <div className="adt-similar-sym">{asset.symbol}</div>
          </div>
        </div>
        <button className={`sv2-star-btn ${asset.watching ? "active" : ""}`} onClick={(e) => e.stopPropagation()}>
          <IconStar size={15} filled={asset.watching} />
        </button>
      </div>

      <div className="adt-similar-price">{formatAssetPrice(asset.price)}</div>
      <div className="adt-similar-price-label">last price</div>

      {asset.sparkline?.length > 1 && (
        <div className="adt-similar-chart">
          <MiniChart color={positive ? "var(--sv2-green)" : "var(--sv2-red)"} data={asset.sparkline} width={260} height={44} />
        </div>
      )}

      <div className="adt-similar-foot">
        <span className={`adt-change ${positive ? "positive" : "negative"}`}>
          {positive ? "↗" : "↘"} {formatPct(Math.abs(asset.change24h))}
        </span>
        {asset.aaiScore != null && <span className="adt-tag-pill sm">AAI {Math.round(asset.aaiScore)}</span>}
        {asset.signal && (
          <span className={`adt-tag-pill sm ${SIGNAL_CLASS[asset.signal] || "neutral"}`}>
            {SIGNAL_LABEL[asset.signal] || asset.signal}
          </span>
        )}
        {asset.held && <span className="adt-tag held sm">Held</span>}
        {asset.watching && <span className="adt-tag sm">Watching</span>}
      </div>
    </div>
  );
}