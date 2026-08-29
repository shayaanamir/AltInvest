import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { formatAssetPrice, formatPct } from "../../utils/formatters";
import { IconArrowLeft, IconStar, IconClock, IconPlus, IconColumns, IconBell } from "../icons";

export default function AssetHeaderCard({ header, onBack }) {
  const navigate = useNavigate();
  const [watching, setWatching] = useState(false);

  if (!header) return null;
  const positive = header.change24h >= 0;

  return (
    <>
      <button className="adt-back-btn" onClick={onBack}>
        <IconArrowLeft size={15} />
        Back
      </button>

      <div className="sv2-card adt-header-card">
        <div className="adt-header-top">
          <div className="adt-header-id">
            <div className="adt-avatar" style={{ background: header.logoColor }}>{header.symbol}</div>
            <div>
              <div className="adt-name-row">
                <span className="adt-name">{header.name}</span>
                {header.subcategory && <span className="adt-tag">{header.subcategory}</span>}
                {header.held && <span className="adt-tag held">Held</span>}
              </div>
              <div className="adt-price-row">
                <span className="adt-price">{formatAssetPrice(header.price)}</span>
                <span className={`adt-change ${positive ? "positive" : "negative"}`}>
                  {positive ? "↗" : "↘"} {formatPct(Math.abs(header.change24h))}
                </span>
                {header.held && header.quantityHeld != null && (
                  <span className="adt-holding-note">you hold {header.quantityHeld} {header.symbol}</span>
                )}
              </div>
            </div>
          </div>

          <div className="adt-header-actions">
            <button className={`adt-action-btn ${watching ? "active" : ""}`} onClick={() => setWatching((w) => !w)}>
              <IconStar size={14} filled={watching} />
              {watching ? "Watching" : "Add to watchlist"}
            </button>

            <button className="adt-action-btn" onClick={() => navigate("/sentiment")}>
              <IconClock size={14} />
              Track sentiment
            </button>

            <button className="adt-action-btn" onClick={() => navigate("/portfolio")}>
              <IconPlus size={14} />
              Add more
            </button>

            <button className="adt-action-btn" onClick={() => navigate("/compare")}>
              <IconColumns size={14} />
              Compare
            </button>

            <button className="adt-action-btn" onClick={() => navigate("/alerts")}>
              <IconBell size={14} />
              Set alert
            </button>
          </div>
        </div>
      </div>
    </>
  );
}