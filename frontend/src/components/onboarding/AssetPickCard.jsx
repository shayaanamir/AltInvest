import { IconCheck2 } from "../icons";
import AssetAvatar from "../shared/AssetAvatar";
import Sparkline from "../charts/Sparkline";
import { formatAssetPrice } from "../../utils/formatters";
import { AAI_BADGE_LABEL, ratingClass } from "../../utils/scoring";

/** One coin or NFT collection in the "follow" step: real price, move, sparkline and AAI reading. */
export default function AssetPickCard({ item, selected, onToggle }) {
  const isNft = item.type === "nft";
  const change = item.changePct;
  const tone = change == null ? "flat" : change >= 0 ? "positive" : "negative";

  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={selected}
      aria-label={`${item.name} ${item.symbol}`}
      className={`ob-asset ${selected ? "is-selected" : ""}`}
      onClick={() => onToggle(item)}
    >
      <span className="ob-check" aria-hidden="true"><IconCheck2 size={13} /></span>

      <span className="ob-asset-top">
        <AssetAvatar symbol={item.symbol} color={item.color} size={34} />
        <span className="ob-asset-id">
          <span className="ob-asset-name" style={{ display: "block" }}>{item.name}</span>
          <span className="ob-asset-sym" style={{ display: "block" }}>{item.symbol}</span>
        </span>
      </span>

      <span className="ob-asset-price-row">
        <span className="ob-asset-price">
          {formatAssetPrice(item.price)}
          {isNft && <span className="ob-asset-sym"> floor</span>}
        </span>
        <span className={`ob-change ${tone}`}>
          {change != null ? `${change >= 0 ? "+" : "−"}${Math.abs(change).toFixed(2)}%` : "—"}
        </span>
      </span>

      <span className="ob-asset-spark" style={{ display: "block" }} aria-hidden="true">
        {!isNft && (
          <Sparkline data={item.sparkline} color={tone === "negative" ? "var(--sv2-red)" : "var(--sv2-green)"} height={30} />
        )}
      </span>

      <span className="ob-asset-foot">
        <span>AAI {item.aaiScore != null ? Math.round(item.aaiScore) : "—"}</span>
        {/* An AAI rating, never Buy/Sell (audit G-37). */}
        {item.signal && <span className={`sv2-signal-pill ${ratingClass(item.signal)}`}>{AAI_BADGE_LABEL[item.signal] ?? item.signal}</span>}
      </span>
    </button>
  );
}
