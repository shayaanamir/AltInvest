import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { onHoldingsChanged } from "../../services/holdingsEvents";
import { useAsync } from "../../hooks/useAsync";
import { portfolioApi } from "../../services/portfolioApi";
import { formatAssetPrice, formatPct } from "../../utils/formatters";
import { getAaiTierColor } from "../../utils/scoring";
import AssetAvatar from "../shared/AssetAvatar";
import { IconPlus, IconPencil, IconTrash, IconBell, IconClock } from "../icons";
import { ErrorState, useToast } from "../../errors";
import AddHoldingModal from "./AddHoldingModal";
import HoldingHistoryModal from "./HoldingHistoryModal";
import CreateAlertModal from "../alerts/CreateAlertModal";

export default function CryptoHoldingsTable() {
  const navigate = useNavigate();
  const toast = useToast();
  const [adding, setAdding] = useState(false);
  const [history, setHistory] = useState(null); // holding whose history is open
  const [editing, setEditing] = useState(null); // holding being edited
  const [alertFor, setAlertFor] = useState(null); // holding an alert is being set on
  const { data: holdings, error, refetch } = useAsync(() => portfolioApi.getCryptoHoldings(), [], { subscribe: onHoldingsChanged });

  return (
    <div className="sv2-card sv2-card-pad">
      <div className="sv2-flex-between sv2-mb-16">
        <div>
          <h2 className="sv2-card-title">Holdings Breakdown</h2>
          <div className="sv2-card-sub">Core portfolio assets with real-time AAI sentiment overlay</div>
        </div>
        <button className="sv2-btn-outline" style={{ flex: "none" }} type="button" onClick={() => setAdding(true)}>
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

        {error ? (
          <ErrorState error={error} onRetry={refetch} title="Couldn't load your holdings" />
        ) : !holdings ? (
          <div className="sv2-muted sv2-small sv2-mt-12">Loading holdings…</div>
        ) : holdings.length === 0 ? (
          <div className="sv2-muted sv2-small sv2-mt-12">No holdings yet — add your first one above.</div>
        ) : (
          holdings.map((h) => {
            const positive = h.change24hPct >= 0;
            return (
              <div key={h.symbol} className="pv2-holdings-row" onClick={() => navigate(`/asset-detail?symbol=${h.symbol}`)}>
                <div className="pv2-asset-cell">
                  <AssetAvatar symbol={h.symbol} color={h.logoColor} size={36} />
                  <div>
                    <div className="pv2-asset-name">{h.name}</div>
                    <div className="pv2-asset-symbol">{h.symbol}</div>
                  </div>
                </div>

                <span className="sv2-small">{h.quantity}</span>
                <span className="sv2-small sv2-bold" title={h.valueUsd == null ? "No current price for this asset" : undefined}>
                  {h.valueUsd == null ? "—" : formatAssetPrice(h.valueUsd)}
                </span>

                <span className={`dv2-asset-change ${positive ? "positive" : "negative"}`}>
                  {positive ? "↗" : "↘"} {formatPct(h.change24hPct, { withSign: true })}
                </span>

                <span className="pv2-aai-pill">
                  <span className="pv2-aai-dot" style={{ background: getAaiTierColor(h.aaiScore) }} />
                  {h.aaiScore != null ? `AAI ${h.aaiScore}` : "AAI —"}
                </span>

                <span className="pv2-suggested-btn">{h.aiAction}</span>

                <div className="pv2-manage-icons" onClick={(e) => e.stopPropagation()}>
                  <button type="button" title="Set alert" aria-label={`Set an alert on ${h.symbol}`} onClick={() => setAlertFor(h)}><IconBell size={14} /></button>
                  <button type="button" title="History" aria-label={`History of ${h.symbol}`} onClick={() => setHistory({ id: h.id, kind: "crypto", name: h.name, symbol: h.symbol, quantity: h.quantity })}><IconClock size={13} /></button>
                  <button type="button" title="Edit" aria-label={`Edit ${h.symbol}`} onClick={() => setEditing(h)}><IconPencil size={13} /></button>
                  <button
                    type="button"
                    title="Remove"
                    onClick={async () => {
                      if (!h.id) return;
                      if (!window.confirm(`Remove ${h.symbol} from your portfolio?`)) return;
                      try {
                        await portfolioApi.removeHolding(h.id);
                        refetch();
                      } catch (e) {
                        toast.error(e, { title: `Couldn't remove ${h.symbol}` });
                      }
                    }}
                  >
                    <IconTrash size={13} />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
      {adding && <AddHoldingModal onClose={() => setAdding(false)} />}
      {history && <HoldingHistoryModal holding={history} onClose={() => setHistory(null)} />}
      {editing && (
        <AddHoldingModal
          holding={{
            id: editing.id, kind: "crypto", assetId: editing.symbol, symbol: editing.symbol, name: editing.name,
            quantity: editing.quantity, price: editing.avgBuyPriceUsd,
          }}
          onClose={() => setEditing(null)}
        />
      )}
      {alertFor && (
        <CreateAlertModal
          target={{ type: "crypto", symbol: alertFor.symbol, name: alertFor.name }}
          hint={alertFor.quantity && alertFor.valueUsd != null ? `Currently ${formatAssetPrice(alertFor.valueUsd / alertFor.quantity)}` : undefined}
          onClose={() => setAlertFor(null)}
        />
      )}
    </div>
  );
}