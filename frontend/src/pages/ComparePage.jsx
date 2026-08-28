import { useState, useEffect } from "react";
import "../styles/sentiment.css";
import "../styles/compare.css";
import CompareEmptyState from "../components/compare/CompareEmptyState";
import CompareAssetModal from "../components/compare/CompareAssetModal";
import CompareAssetCard from "../components/compare/CompareAssetCard";
import CompareAaiChart from "../components/compare/CompareAaiChart";
import CompareRiskReturnChart from "../components/compare/CompareRiskReturnChart";
import CompareSentimentTable from "../components/compare/CompareSentimentTable";
import { IconColumns } from "../components/icons";
import { compareApi } from "../services/compareApi";

export default function ComparePage() {
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState([]);
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (selectedIds.length === 0) {
      setAssets([]);
      return;
    }
    setLoading(true);
    compareApi.getByIds(selectedIds).then((a) => {
      setAssets(a);
      setLoading(false);
    });
  }, [selectedIds]);

  const handleConfirm = (ids) => {
    setSelectedIds(ids);
    setModalOpen(false);
  };

  const removeAsset = (id) => {
    setSelectedIds((prev) => prev.filter((x) => x !== id));
  };

  const hasSelection = selectedIds.length >= 2;

  return (
    <div className="sv2">
      <div className="sv2-page cmp-page">
        <div className="cmp-page-head">
          <div>
            <h1 className="sv2-h1">Compare</h1>
            <p className="sv2-lead">
              {hasSelection
                ? "Side by side on the dimensions that matter."
                : "Put two to four assets side by side — any mix of categories."}
            </p>
          </div>
          {hasSelection && (
            <button className="cmp-edit-btn" onClick={() => setModalOpen(true)}>
              <IconColumns size={16} /> Edit selection
            </button>
          )}
        </div>

        {!hasSelection ? (
          <CompareEmptyState onChooseAssets={() => setModalOpen(true)} />
        ) : loading || assets.length === 0 ? (
          <div className="sv2-muted sv2-small">Loading comparison…</div>
        ) : (
          <div className="cmp-flex-col">
            <div className="cmp-asset-cards-grid" data-count={assets.length}>
              {assets.map((a) => (
                <CompareAssetCard key={a.id} asset={a} onRemove={removeAsset} />
              ))}
            </div>
            <div className="cmp-charts-grid">
              <CompareAaiChart assets={assets} />
              <CompareRiskReturnChart assets={assets} />
            </div>
            <CompareSentimentTable assets={assets} />
          </div>
        )}

        {modalOpen && (
          <CompareAssetModal
            initialSelected={selectedIds}
            onClose={() => setModalOpen(false)}
            onConfirm={handleConfirm}
          />
        )}
      </div>
    </div>
  );
}