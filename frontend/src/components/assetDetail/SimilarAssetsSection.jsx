import { useNavigate } from "react-router-dom";
import { useAsync } from "../../hooks/useAsync";
import { assetDetailApi } from "../../services/assetDetailApi";
import SimilarAssetCard from "./SimilarAssetCard";

export default function SimilarAssetsSection({ symbol, relatedAssets }) {
  const navigate = useNavigate();
  const { data: assets } = useAsync(() => assetDetailApi.getSimilarAssets(symbol, relatedAssets), [symbol, relatedAssets]);

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