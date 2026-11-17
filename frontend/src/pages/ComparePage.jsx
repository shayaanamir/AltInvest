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
  const [reloadTick, setReloadTick] = useState(0);

  // When the link or router state names two or more assets, that becomes the selection. This is
  // picked up while rendering (a change of the ids, not of every render), not in an effect.
  const stateIds = location.state?.ids;
  const paramIds = searchParams.get("ids");
  const targetIds = stateIds || (paramIds ? paramIds.split(",").filter(Boolean) : null);
  const targetKey = targetIds && targetIds.length >= 2 ? targetIds.join(",") : null;
  const [syncedKey, setSyncedKey] = useState(targetKey); // the first selection above already came from the same place
  if (targetKey !== syncedKey) {
    setSyncedKey(targetKey);
    if (targetKey) setSelectedIds(targetIds);
  }

  // The newest answer, tagged with the request it belongs to. Loading is "no answer for this request yet".
  const [fetched, setFetched] = useState({ key: null, assets: [], error: null });
  const requestKey = `${selectedIds.join(",")}|${reloadTick}`;
  const loading = selectedIds.length > 0 && fetched.key !== requestKey;
  const assets = selectedIds.length === 0 ? [] : fetched.assets;
  const error = fetched.key === requestKey ? fetched.error : null;

  useEffect(() => {
    if (selectedIds.length === 0) return undefined;
    let cancelled = false;
    compareApi.getByIds(selectedIds)
      .then((a) => { if (!cancelled) setFetched({ key: requestKey, assets: a, error: null }); })
      .catch((e) => { if (!cancelled) { console.error(e); setFetched({ key: requestKey, assets: [], error: e }); } });
    return () => { cancelled = true; };
  }, [selectedIds, requestKey]);

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