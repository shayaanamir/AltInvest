import { useState, useEffect } from "react";
import { useSearchParams, useLocation } from "react-router-dom";
import "../styles/compare.css";
import CompareEmptyState from "../components/compare/CompareEmptyState";
import CompareAssetModal from "../components/compare/CompareAssetModal";
import CompareAssetCard from "../components/compare/CompareAssetCard";
import CompareAaiChart from "../components/compare/CompareAaiChart";
import CompareRiskReturnChart from "../components/compare/CompareRiskReturnChart";
import CompareSentimentTable from "../components/compare/CompareSentimentTable";
import { IconColumns } from "../components/icons";
import { compareApi } from "../services/compareApi";
import { ErrorState } from "../errors";

export default function ComparePage() {
  const [searchParams] = useSearchParams();
  const location = useLocation();

  const [modalOpen, setModalOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState(() => {
    if (location.state?.ids) return location.state.ids;
    const paramIds = searchParams.get("ids");
    if (paramIds) return paramIds.split(",").filter(Boolean);
    return [];
  });
  const [assets, setAssets] = useState([]);
  const [reloadTick, setReloadTick] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const stateIds = location.state?.ids;
    const paramIds = searchParams.get("ids");
    const targetIds = stateIds || (paramIds ? paramIds.split(",").filter(Boolean) : null);
    if (targetIds && targetIds.length >= 2) {
      setSelectedIds(targetIds);
    }
  }, [location.state, searchParams]);

  useEffect(() => {
    if (selectedIds.length === 0) {
      setAssets([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    compareApi.getByIds(selectedIds)
      .then((a) => { if (!cancelled) setAssets(a); })
      .catch((e) => { if (!cancelled) { console.error(e); setAssets([]); setError(e); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [selectedIds, reloadTick]);

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
        ) : loading ? (
          <div className="sv2-muted sv2-small">Loading comparison…</div>
        ) : error ? (
          <div className="sv2-card sv2-card-pad">
            <ErrorState error={error} onRetry={() => setReloadTick((t) => t + 1)} variant="panel" title="Couldn't load the comparison" />
          </div>
        ) : assets.length < 2 ? (
          <div className="sv2-muted sv2-small">
            Fewer than two of the selected items exist in the database. Edit the selection to pick covered assets.
          </div>
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
            initialSelection={selectedIds}
            onClose={() => setModalOpen(false)}
            onConfirm={handleConfirm}
          />
        )}
      </div>
    </div>
  );
}