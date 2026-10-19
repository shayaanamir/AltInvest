import { useState, useCallback } from "react";
import { ErrorState, useToast } from "../../errors";
import { useAsync } from "../../hooks/useAsync";
import { sentimentApi } from "../../services/sentimentApi";
import { fetchAssetStatus } from "../../services/assetRepository";
import { onHoldingsChanged, onWatchlistsChanged } from "../../services/holdingsEvents";
import CreateAlertModal from "../alerts/CreateAlertModal";
import AddHoldingModal from "../portfolio/AddHoldingModal";
import WatchlistPickerModal from "../watchlists/WatchlistPickerModal";
import AssetDetailHeader from "./AssetDetailHeader";
import AssetReadCard from "./AssetReadCard";
import AssetOverTimeChart from "./AssetOverTimeChart";
import WhatsDrivingIt from "./WhatsDrivingIt";
import AssetActionsPanel from "./AssetActionsPanel";
import AssetAlertsPanel from "./AssetAlertsPanel";
import WhatWeReadList from "./WhatWeReadList";
import MarketContextPanel from "./MarketContextPanel";

export default function AssetSentimentDetail({ assetId, colors, onBack, onSwitchAsset }) {
  const toast = useToast();
  const { data: detail, error, refetch, setData: setDetail } = useAsync(() => sentimentApi.getAssetDetail(assetId), [assetId]);
  const { data: switchableRaw } = useAsync(() => sentimentApi.getSwitchableAssets(), []);
  const switchable = switchableRaw || [];
  const [refreshing, setRefreshing] = useState(false);
  // Whether the signed-in user holds / watches this asset (null: not in the covered universe).
  const subscribeStatus = useCallback((handler) => {
    const offHoldings = onHoldingsChanged(handler);
    const offLists = onWatchlistsChanged(handler);
    return () => { offHoldings(); offLists(); };
  }, []);
  const { data: status } = useAsync(
    () => (detail?.category === "nft" ? Promise.resolve(null) : fetchAssetStatus(assetId.toUpperCase())),
    [assetId, detail?.category],
    { subscribe: subscribeStatus }
  );
  const [dialog, setDialog] = useState(null); // "alert" | "watch" | "hold"
  const [alertsVersion, setAlertsVersion] = useState(0);
  const covered = !!status;

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const fresh = await sentimentApi.refreshAsset(assetId);
      setDetail(fresh);
    } catch (e) {
      toast.error(e, { title: "Couldn't refresh sentiment" });
    } finally {
      setRefreshing(false);
    }
  };

  if (error) {
    return (
      <div className="sv2-card sv2-card-pad">
        <ErrorState error={error} onRetry={refetch} variant="panel" title="Couldn't load this asset's sentiment" />
        <div className="err-state-actions" style={{ justifyContent: "center" }}>
          <button type="button" className="err-btn" onClick={onBack}>Back</button>
        </div>
      </div>
    );
  }

  if (!detail) {
    return <div className="sv2-muted sv2-small">Loading asset sentiment…</div>;
  }

  return (
    <div className="sv2-flex-col sv2-gap-16">
      <AssetDetailHeader
        detail={detail}
        switchable={switchable}
        onBack={onBack}
        onSwitchAsset={onSwitchAsset}
        onRefresh={handleRefresh}
        refreshing={refreshing}
        watching={!!status?.watching}
        onToggleWatching={() => setDialog("watch")}
        watchDisabled={!covered}
      />

      <div className="sv2-detail-grid">
        <div className="sv2-flex-col sv2-gap-16">
          <AssetReadCard detail={detail} colors={colors} />
          <div className="sv2-subgrid-2">
            <AssetOverTimeChart assetId={detail.assetId} trend={detail.trend} colors={colors} />
            <WhatsDrivingIt detail={detail} colors={colors} />
          </div>
        </div>
        <div className="sv2-flex-col sv2-gap-16">
          <AssetActionsPanel
            symbol={assetId.toUpperCase()}
            status={status}
            onAlert={() => setDialog("alert")}
            onWatch={() => setDialog("watch")}
            onHold={() => setDialog("hold")}
          />
          <AssetAlertsPanel
            symbol={assetId.toUpperCase()}
            covered={covered}
            version={alertsVersion}
            onNewAlert={() => setDialog("alert")}
          />
        </div>
      </div>

      {dialog === "alert" && covered && (
        <CreateAlertModal
          target={{ type: "crypto", symbol: status.symbol, name: status.name }}
          defaults={{ metric: "sentiment", condition: "shifts_bearish" }}
          onClose={() => setDialog(null)}
          onCreated={() => setAlertsVersion((v) => v + 1)}
        />
      )}
      {dialog === "watch" && covered && (
        <WatchlistPickerModal item={{ type: "crypto", id: status.id, name: status.name }} onClose={() => setDialog(null)} />
      )}
      {dialog === "hold" && covered && (
        <AddHoldingModal initialKind="crypto" initialAssetId={status.id} onClose={() => setDialog(null)} />
      )}

      <WhatWeReadList detail={detail} colors={colors} />
      <MarketContextPanel detail={detail} />
    </div>
  );
}