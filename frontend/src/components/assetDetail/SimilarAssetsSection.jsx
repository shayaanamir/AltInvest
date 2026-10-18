import { useNavigate } from "react-router-dom";
import SimilarAssetCard from "./SimilarAssetCard";

export default function SimilarAssetsSection({ assets }) {
  const navigate = useNavigate();

  return (
    <div className="adt-similar-section">
      <div className="adt-similar-head">
        <div className="sv2-card-title" style={{ fontSize: 18 }}>Similar assets</div>
        <button className="adt-similar-link" onClick={() => navigate("/compare")}>
          Compare with one →
        </button>
      </div>
      <div className="adt-similar-grid">
        {assets.length === 0 ? (
          <div className="sv2-muted sv2-small">No similar assets in the database.</div>
        ) : (
          assets.map((a) => <SimilarAssetCard key={a.symbol} asset={a} />)
        )}
      </div>
    </div>
  );
}
