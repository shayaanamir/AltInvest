import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { dashboardApi } from "../../services/dashboardApi";
import { formatAssetPrice, formatPct } from "../../utils/formatters";
import { getAaiTierClass } from "../../utils/scoring";
import Sparkline from "../charts/Sparkline";
import { IconStar } from "../icons";

export default function TrendingAssetsSection() {
  const [assets, setAssets] = useState(null);
  const [favorites, setFavorites] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    dashboardApi.getTrendingAssets().then(setAssets).catch(console.error);
  }, []);

  const toggleFavorite = (symbol) =>
    setFavorites((f) => (f.includes(symbol) ? f.filter((x) => x !== symbol) : [...f, symbol]));

  return (
    <section>
      <div className="dv2-section-head">
        <div>
          <h2 className="dv2-section-title">Trending assets</h2>
          <p className="dv2-section-sub">Weighted toward the markets you chose and what you already follow</p>
        </div>
        <a href="#" className="dv2-section-link" onClick={(e) => { e.preventDefault(); navigate("/asset-detail"); }}>
          See all →
        </a>
      </div>

      <div className="dv2-asset-grid">
        {!assets ? (
          <div className="sv2-muted sv2-small">Loading trending assets…</div>
        ) : (
          assets.map((a) => {
            const positive = a.change24h >= 0;
            const watching = a.watching || favorites.includes(a.symbol);
            return (
              <div
                key={a.symbol}
                className="sv2-card dv2-asset-card"
                style={{ cursor: "pointer" }}
                onClick={() => navigate("/asset-detail")}
              >
                <div className="dv2-asset-card-top">
                  <div className="dv2-asset-id">
                    <div className="dv2-asset-avatar" style={{ background: a.logoColor || "var(--sv2-accent)" }}>
                      {a.symbol.slice(0, 3)}
                    </div>
                    <div>
                      <div className="dv2-asset-name">{a.name}</div>
                      <div className="dv2-asset-sym">{a.symbol}</div>
                    </div>
                  </div>
                  <button
                    className={`sv2-star-btn ${watching ? "active" : ""}`}
                    onClick={(e) => { e.stopPropagation(); toggleFavorite(a.symbol); }}
                  >
                    <IconStar size={16} filled={watching} />
                  </button>
                </div>

                <div className="dv2-asset-price-row">
                  <div>
                    <div className="dv2-asset-price">{formatAssetPrice(a.price)}</div>
                    <div className="dv2-asset-price-label">last price</div>
                  </div>
                  <span className={`dv2-asset-change ${positive ? "positive" : "negative"}`}>
                    {positive ? "↗" : "↘"} {formatPct(a.change24h, { withSign: true })}
                  </span>
                </div>

                <div className="dv2-asset-chart">
                  <Sparkline color={positive ? "var(--sv2-green)" : "var(--sv2-red)"} data={a.sparkline} width={220} height={44} />
                </div>

                <div className="dv2-asset-badges">
                  <span className={`dv2-badge dv2-badge-aai ${getAaiTierClass(a.aai?.score)}`}>
                    AAI {Math.round(a.aai?.score ?? 0)}
                  </span>
                  <span className="sv2-badge-pill">{a.aai?.signal}</span>
                  {watching && (
                    <span className="sv2-badge-pill dv2-badge-watching" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                      <IconStar size={11} filled={true} /> Watching
                    </span>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </section>
  );
}