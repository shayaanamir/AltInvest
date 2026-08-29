import { useNavigate } from "react-router-dom";
import { useAsync } from "../../hooks/useAsync";
import { portfolioApi } from "../../services/portfolioApi";
import { formatAssetPrice, formatPct } from "../../utils/formatters";
import { getAaiTierColor } from "../../utils/scoring";
import AssetAvatar from "../shared/AssetAvatar";
import { IconPlus, IconPencil, IconTrash, IconBell } from "../icons";

export default function CryptoHoldingsTable() {
  const navigate = useNavigate();
  const { data: holdings } = useAsync(() => portfolioApi.getCryptoHoldings(), []);

  return (
    <div className="sv2-card sv2-card-pad">
      <div className="sv2-flex-between sv2-mb-16">
        <div>
          <h2 className="sv2-card-title">Holdings Breakdown</h2>
          <div className="sv2-card-sub">Core portfolio assets with real-time AAI sentiment overlay</div>
        </div>
        <button className="sv2-btn-outline" style={{ flex: "none" }} type="button">
          <IconPlus size={14} /> Add holding
        </button>
      </div>

      <div className="pv2-holdings-table">
        <div className="pv2-holdings-row pv2-holdings-head">
          <span>Asset</span>
          <span>Quantity</span>
          <span>Value</span>
          <span>24h Change</span>
          <span>AAI Read</span>
          <span>AI Suggestion</span>
          <span style={{ textAlign: "right" }}>Manage</span>
        </div>

        {!holdings ? (
          <div className="sv2-muted sv2-small sv2-mt-12">Loading holdings…</div>
        ) : (
          holdings.map((h) => {
            const positive = h.change24hPct >= 0;
            return (
              <div key={h.symbol} className="pv2-holdings-row" onClick={() => navigate("/asset-detail")}>
                <div className="pv2-asset-cell">
                  <AssetAvatar symbol={h.symbol} color={h.logoColor} size={36} />
                  <div>
                    <div className="pv2-asset-name">{h.name}</div>
                    <div className="pv2-asset-symbol">{h.symbol}</div>
                  </div>
                </div>

                <span className="sv2-small">{h.quantity}</span>
                <span className="sv2-small sv2-bold">{formatAssetPrice(h.valueUsd)}</span>

                <span className={`dv2-asset-change ${positive ? "positive" : "negative"}`}>
                  {positive ? "↗" : "↘"} {formatPct(h.change24hPct, { withSign: true })}
                </span>

                <span className="pv2-aai-pill">
                  <span className="pv2-aai-dot" style={{ background: getAaiTierColor(h.aaiScore) }} />

                  AAI {h.aaiScore}
                </span>

                <span className="pv2-suggested-btn">{h.aiAction}</span>

                <div className="pv2-manage-icons" onClick={(e) => e.stopPropagation()}>
                  <button type="button" title="Set alert"><IconBell size={14} /></button>
                  <button type="button" title="Edit"><IconPencil size={13} /></button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}