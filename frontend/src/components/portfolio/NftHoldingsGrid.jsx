import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { portfolioApi } from "../../services/portfolioApi";
import { formatPct } from "../../utils/formatters";
import NftArtPlaceholder from "./NftArtPlaceholder";

export default function NftHoldingsGrid() {
  const navigate = useNavigate();
  const [holdings, setHoldings] = useState(null);

  useEffect(() => {
    portfolioApi.getNftHoldings().then(setHoldings).catch(console.error);
  }, []);

  return (
    <div className="sv2-card sv2-card-pad" style={{ marginTop: 10 }}>
      <div className="sv2-card-title">NFT holdings</div>
      <div className="sv2-card-sub" style={{ marginBottom: 14 }}>Valued against current collection floor</div>

      {!holdings ? (
        <div className="sv2-muted sv2-small" style={{ padding: "24px 0" }}>Loading…</div>
      ) : holdings.length === 0 ? (
        <div className="sv2-muted sv2-small" style={{ padding: "24px 0" }}>No NFTs in this portfolio yet.</div>
      ) : (
        <div className="pv2-nft-grid">
          {holdings.map((n) => {
            const positive = n.changePct >= 0;
            return (
              <div
                key={`${n.collectionSlug}-${n.tokenId}`}
                className="sv2-card pv2-nft-card"
                onClick={() => navigate("/asset-detail")}
              >
                <div className="pv2-nft-art">
                  <NftArtPlaceholder color={n.artColor} seed={Number(n.tokenId) || 1} />
                </div>
                <div className="pv2-nft-body">
                  <div className="pv2-nft-name">{n.collectionName}</div>
                  <div className="pv2-nft-token">#{n.tokenId}</div>
                  <div className="pv2-nft-price-row">
                    <div>
                      <div className="pv2-nft-price">{n.currentPriceEth} ETH</div>
                      <div className="pv2-nft-cost">cost {n.avgBuyPriceEth} ETH</div>
                    </div>
                    <span className={`dv2-asset-change ${positive ? "positive" : "negative"}`}>
                      {positive ? "↗" : "↘"} {formatPct(n.changePct, { withSign: true })}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}