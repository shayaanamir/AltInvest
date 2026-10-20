import { useState } from "react";
import { useAsync } from "../../hooks/useAsync";
import { onHoldingsChanged } from "../../services/holdingsEvents";
import { portfolioApi } from "../../services/portfolioApi";
import { ErrorState, useToast } from "../../errors";
import { IconPlus, IconPencil, IconTrash, IconBell, IconClock } from "../icons";
import AddHoldingModal from "./AddHoldingModal";
import HoldingHistoryModal from "./HoldingHistoryModal";
import CreateAlertModal from "../alerts/CreateAlertModal";
import { formatPct } from "../../utils/formatters";
import NftArtPlaceholder from "./NftArtPlaceholder";

export default function NftHoldingsGrid() {
  const toast = useToast();
  const [adding, setAdding] = useState(false);
  const [history, setHistory] = useState(null); // holding whose history is open
  const [editing, setEditing] = useState(null);
  const [alertFor, setAlertFor] = useState(null);
  const { data: holdings, error, refetch } = useAsync(() => portfolioApi.getNftHoldings(), [], { subscribe: onHoldingsChanged });

  return (
    <div className="sv2-card sv2-card-pad" style={{ marginTop: 10 }}>
      <div className="sv2-flex-between" style={{ marginBottom: 14 }}>
        <div>
          <div className="sv2-card-title">NFT holdings</div>
          <div className="sv2-card-sub">Valued against current collection floor</div>
        </div>
        <button className="sv2-btn-outline" style={{ flex: "none" }} type="button" onClick={() => setAdding(true)}>
          <IconPlus size={14} /> Add NFT
        </button>
      </div>

      {error ? (
        <ErrorState error={error} onRetry={refetch} title="Couldn't load NFT holdings" />
      ) : !holdings ? (
        <div className="sv2-muted sv2-small" style={{ padding: "24px 0" }}>Loading…</div>
      ) : holdings.length === 0 ? (
        <div className="sv2-muted sv2-small" style={{ padding: "24px 0" }}>No NFTs in this portfolio yet — add one above.</div>
      ) : (
        <div className="pv2-nft-grid">
          {holdings.map((n) => {
            const positive = n.changePct >= 0;
            return (
              <div
                key={n.id || `${n.collectionSlug}-${n.tokenId}`}
                className="sv2-card pv2-nft-card"
                style={{ cursor: "default" }}
              >
                <div className="pv2-nft-art">
                  <NftArtPlaceholder color={n.artColor} seed={Number(n.tokenId) || 1} />
                </div>
                <div className="pv2-nft-body">
                  <div className="pv2-nft-name">{n.collectionName}</div>
                  <div className="pv2-nft-token">#{n.tokenId}</div>
                  <div className="pv2-nft-price-row">
                    <div>
                      <div className="pv2-nft-price">{n.currentPriceEth} ETH</div>
                      <div className="pv2-nft-cost">cost {n.avgBuyPriceEth} ETH</div>
                    </div>
                    <span className={`dv2-asset-change ${positive ? "positive" : "negative"}`}>
                      {positive ? "↗" : "↘"} {formatPct(n.changePct, { withSign: true })}
                    </span>
                  </div>
                  <div className="pv2-manage-icons" style={{ marginTop: 10 }}>
                    <button type="button" title="Set alert" aria-label={`Set an alert on ${n.collectionName}`} onClick={() => setAlertFor(n)}><IconBell size={14} /></button>
                    <button type="button" title="History" aria-label={`History of ${n.collectionName}`} onClick={() => setHistory({ id: n.id, kind: "nft", name: `${n.collectionName} #${n.tokenId}`, symbol: null, quantity: n.quantity })}><IconClock size={13} /></button>
                    <button type="button" title="Edit" aria-label={`Edit ${n.collectionName} #${n.tokenId}`} onClick={() => setEditing(n)}><IconPencil size={13} /></button>
                    <button
                      type="button"
                      title="Remove"
                      aria-label={`Remove ${n.collectionName} #${n.tokenId}`}
                      onClick={async () => {
                        if (!n.id) return;
                        if (!window.confirm(`Remove ${n.collectionName} #${n.tokenId} from your portfolio?`)) return;
                        try {
                          await portfolioApi.removeHolding(n.id);
                        } catch (e) {
                          toast.error(e, { title: `Couldn't remove ${n.collectionName}` });
                        }
                      }}
                    >
                      <IconTrash size={13} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
      {adding && <AddHoldingModal initialKind="nft" onClose={() => setAdding(false)} />}
      {history && <HoldingHistoryModal holding={history} onClose={() => setHistory(null)} />}
      {editing && (
        <AddHoldingModal
          holding={{
            id: editing.id, kind: "nft", assetId: editing.collectionSlug, symbol: null, name: editing.collectionName,
            tokenId: editing.tokenId, quantity: editing.quantity, price: editing.avgBuyPriceEth,
          }}
          onClose={() => setEditing(null)}
        />
      )}
      {alertFor && (
        <CreateAlertModal
          target={{ type: "nft", slug: alertFor.collectionSlug, name: alertFor.collectionName }}
          hint={alertFor.currentPriceEth != null ? `Floor is currently ${alertFor.currentPriceEth} ETH` : undefined}
          onClose={() => setAlertFor(null)}
        />
      )}
    </div>
  );
}