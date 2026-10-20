import { deriveAaiSignal } from "../../services/assetDetailApi";
import { formatAssetPrice } from "../../utils/formatters";
import { formatDate, useAppPreferences } from "../../services/appPreferences";

/** Description, website and all-time high for the asset; hidden when the database has none of them. */
export default function AboutAssetCard({ name, about, aaiScore }) {
  useAppPreferences();
  if (!about || !(about.description || about.website || about.allTimeHigh != null)) return null;
  const signal = aaiScore != null ? deriveAaiSignal(aaiScore) : null;
  const host = about.website ? about.website.replace(/^https?:\/\//, "").replace(/\/$/, "") : null;

  return (
    <div className="sv2-card adt-about-card">
      <div className="sv2-card-title adt-mb-10">About {name}</div>
      {about.description ? (
        <p className="adt-about-text">{about.description}</p>
      ) : (
        <p className="adt-about-text sv2-muted">No description is stored for {name} yet.</p>
      )}
      <div className="adt-about-facts">
        {about.allTimeHigh != null && (
          <span>All-time high <strong>{formatAssetPrice(about.allTimeHigh)}</strong>{about.athDate ? ` on ${formatDate(about.athDate)}` : ""}</span>
        )}
        {host && (
          <a href={about.website} target="_blank" rel="noopener noreferrer">{host} ↗</a>
        )}
      </div>
      {signal && (
        <div className="adt-about-tags">
          <span className="adt-tag-pill">AAI {Math.round(aaiScore)}</span>
          <span className={`adt-tag-pill ${signal.tone}`}>{signal.label.replace("Strong ", "")}</span>
        </div>
      )}
      {about.source === "coingecko" && <div className="adt-about-source">Profile from CoinGecko</div>}
    </div>
  );
}
