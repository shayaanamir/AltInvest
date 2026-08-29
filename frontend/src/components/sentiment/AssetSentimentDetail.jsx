import { useState, useEffect } from "react";
import { useAsync } from "../../hooks/useAsync";
import { sentimentApi, WATCHLIST } from "../../services/sentimentApi";
import AssetDetailHeader from "./AssetDetailHeader";
import AssetReadCard from "./AssetReadCard";
import AssetOverTimeChart from "./AssetOverTimeChart";
import WhatsDrivingIt from "./WhatsDrivingIt";
import AssetActionsPanel from "./AssetActionsPanel";
import AssetAlertsPanel from "./AssetAlertsPanel";
import WhatWeReadList from "./WhatWeReadList";
import MarketContextPanel from "./MarketContextPanel";

export default function AssetSentimentDetail({ assetId, colors, onBack, onSwitchAsset }) {
  const { data: detail, setData: setDetail } = useAsync(() => sentimentApi.getAssetDetail(assetId), [assetId]);
  const { data: switchableRaw } = useAsync(() => sentimentApi.getSwitchableAssets(), []);
  const switchable = switchableRaw || [];
  const [refreshing, setRefreshing] = useState(false);
  const [watching, setWatching] = useState(WATCHLIST.includes(assetId));

  useEffect(() => { setWatching(WATCHLIST.includes(assetId)); }, [assetId]);

  const handleRefresh = async () => {
    setRefreshing(true);
    const fresh = await sentimentApi.refreshAsset(assetId);
    setDetail(fresh);
    setRefreshing(false);
  };

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
        watching={watching}
        onToggleWatching={() => setWatching((w) => !w)}
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
          <AssetActionsPanel watching={watching} onToggleWatching={() => setWatching((w) => !w)} held={detail.held} />
          <AssetAlertsPanel />
        </div>
      </div>

      <WhatWeReadList detail={detail} colors={colors} />
      <MarketContextPanel detail={detail} />
    </div>
  );
}