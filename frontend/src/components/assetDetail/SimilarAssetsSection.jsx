import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { assetDetailApi } from "../../services/assetDetailApi";
import SimilarAssetCard from "./SimilarAssetCard";

export default function SimilarAssetsSection({ symbol, relatedAssets }) {
  const navigate = useNavigate();
  const [assets, setAssets] = useState(null);

  useEffect(() => {
    setAssets(null);
    assetDetailApi.getSimilarAssets(symbol, relatedAssets).then(setAssets).catch(console.error);
  }, [symbol, relatedAssets]);

  return (
    <div className="adt-similar-section">
      <div className="adt-similar-head">
        <div className="sv2-card-title" style={{ fontSize: 18 }}>Similar assets</div>
        <button className="adt-similar-link" onClick={() => navigate("/compare")}>
          Compare with one →
        </button>
      </div>
      <div className="adt-similar-grid">
        {!assets ? (
          <div className="sv2-muted sv2-small">Loading similar assets…</div>
        ) : (
          assets.map((a) => <SimilarAssetCard key={a.symbol} asset={a} />)
        )}
      </div>
    </div>
  );
}