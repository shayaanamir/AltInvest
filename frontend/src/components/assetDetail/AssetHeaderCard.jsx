import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { formatAssetPrice, formatPct } from "../../utils/formatters";

export default function AssetHeaderCard({ header, onBack }) {
  const navigate = useNavigate();
  const [watching, setWatching] = useState(false);

  if (!header) return null;
  const positive = header.change24h >= 0;

  return (
    <>
      <button className="adt-back-btn" onClick={onBack}>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M19 12H5M12 19l-7-7 7-7" />
        </svg>
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
              <svg width="14" height="14" viewBox="0 0 24 24" fill={watching ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.8">
                <path d="M12 2.5l2.9 6.4 6.9.7-5.2 4.7 1.5 6.9L12 17.6l-6.1 3.6 1.5-6.9-5.2-4.7 6.9-.7z" />
              </svg>
              {watching ? "Watching" : "Add to watchlist"}
            </button>

            <button className="adt-action-btn" onClick={() => navigate("/sentiment")}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" />
              </svg>
              Track sentiment
            </button>

            <button className="adt-action-btn" onClick={() => navigate("/portfolio")}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M5 12h14" /></svg>
              Add more
            </button>

            <button className="adt-action-btn" onClick={() => navigate("/compare")}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <rect x="4" y="3" width="6" height="18" rx="1.5" /><rect x="14" y="3" width="6" height="18" rx="1.5" />
              </svg>
              Compare
            </button>

            <button className="adt-action-btn" onClick={() => navigate("/alerts")}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M18 8a6 6 0 10-12 0c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.7 21a2 2 0 01-3.4 0" />
              </svg>
              Set alert
            </button>
          </div>
        </div>
      </div>
    </>
  );
}