import { useNavigate } from "react-router-dom";
import { useAsync } from "../../hooks/useAsync";
import { dashboardApi } from "../../services/dashboardApi";
import { formatPct } from "../../utils/formatters";
import { getAaiTierClass } from "../../utils/scoring";

export default function TrendingCollectionsSection() {
  const { data: collections } = useAsync(() => dashboardApi.getTrendingCollections(), []);
  const navigate = useNavigate();

  return (
    <section style={{ marginTop: 30 }}>
      <div className="dv2-section-head">
        <div>
          <h2 className="dv2-section-title">Trending collections</h2>
          <p className="dv2-section-sub">Floor price and AAI across covered NFT collections</p>
        </div>
        <a href="#" className="dv2-section-link" onClick={(e) => { e.preventDefault(); navigate("/asset-detail"); }}>
          See all →
        </a>
      </div>

      <div className="dv2-collection-grid">
        {!collections ? (
          <div className="sv2-muted sv2-small">Loading trending collections…</div>
        ) : (
          collections.map((c) => {
            const positive = c.change24h >= 0;
            return (
              <div
                key={c.slug}
                className="sv2-card dv2-collection-card"
                style={{ cursor: "pointer" }}
                onClick={() => navigate("/asset-detail")}
              >
                {/* No image field in nftCollections.json — a tinted gradient
                    derived from each collection's own bannerColor stands in
                    for cover art rather than a hardcoded picture. */}
                <div
                  className="dv2-collection-art"
                  style={{ background: `linear-gradient(135deg, ${c.bannerColor}66, ${c.bannerColor}1a)` }}
                />
                <div className="dv2-collection-body">
                  <div className="dv2-collection-top">
                    <span className="dv2-collection-name">{c.name}</span>
                    <span className={`dv2-badge dv2-badge-aai ${getAaiTierClass(c.aai?.score)}`}>
                      AAI {Math.round(c.aai?.score ?? 0)}
                    </span>
                  </div>
                  <div className="dv2-collection-price-row">
                    <div>
                      <div className="dv2-collection-price">{c.floorEth.toFixed(2)} ETH</div>
                      <div className="dv2-collection-price-label">floor price</div>
                    </div>
                    <span className={`dv2-asset-change ${positive ? "positive" : "negative"}`}>
                      {positive ? "↗" : "↘"} {formatPct(c.change24h, { withSign: true })}
                    </span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </section>
  );
}