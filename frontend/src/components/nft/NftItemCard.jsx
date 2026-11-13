import { useState } from "react";
import { useAsync } from "../../hooks/useAsync";
import { nftApi } from "../../services/nftApi";
import { NFT_ITEM_CAPTION, validTokenId } from "../../utils/nftItemValue";
import { ErrorState } from "../../errors";

// Item card (Phase 10 step 10.7, ml/docs/DECISIONS.md D78): estimated value in ETH (point only, no range,
// no drivers), the last floor and its date, the item's last sale, its rarity rank and the served accuracy line.
export default function NftItemCard({ slug, initialToken }) {
  const [input, setInput] = useState(initialToken || "");
  const [query, setQuery] = useState(validTokenId(initialToken));
  const [invalid, setInvalid] = useState(false);
  const { data: v, loading, error, refetch } = useAsync(
    () => (query ? nftApi.getItemValue(slug, query) : Promise.resolve(undefined)), [slug, query]);

  const submit = (e) => {
    e.preventDefault();
    const token = validTokenId(input);
    setInvalid(!token);
    if (token) setQuery(token);
  };

  return (
    <div className="sv2-card sv2-card-pad nft-item-card">
      <div className="sv2-flex-between nft-item-head">
        <div>
          <div className="sv2-card-title">Item value</div>
          <div className="sv2-card-sub">Look up one item of this collection by its token number</div>
        </div>
        <form className="nft-item-form" onSubmit={submit}>
          <input className="nft-item-input" inputMode="numeric" aria-label="Token number" placeholder="Token #"
                 value={input} onChange={(e) => setInput(e.target.value)} />
          <button className="sv2-btn-outline" type="submit" style={{ flex: "none" }}>Look up</button>
        </form>
      </div>

      {invalid ? (
        <div className="sv2-muted sv2-small">Enter a token number (digits only).</div>
      ) : !query ? null : loading ? (
        <div className="sv2-muted sv2-small">Estimating #{query}…</div>
      ) : error ? (
        <ErrorState error={error} onRetry={refetch} variant="panel" title={`Couldn't estimate #${query}`} />
      ) : v === null ? (
        <div className="sv2-muted sv2-small">Token #{query} is not in this collection.</div>
      ) : v ? (
        <div className="nft-item-body">
          <div className="nft-item-token">#{v.tokenId}</div>
          <div className="adt-panel-label">Estimated value</div>
          <div className="nft-big-number">{v.estimateLabel}</div>
          <div className="nft-kv">
            <span>Last floor</span><b>{v.floorLabel} <span className="sv2-mute2">({v.floorDate})</span></b>
            <span>This item's last sale</span><b>{v.lastSaleLabel}</b>
            <span>Rarity rank</span><b>{v.rarityLabel}</b>
            <span>Method</span><b>{v.method}</b>
          </div>
          <div className="nft-item-accuracy">{v.accuracyLine}</div>
          {v.note && <div className="nft-note">{v.note}</div>}
          {v.stale && <div className="nft-note">Showing the last stored estimate ({v.asOf}); the live estimate is unavailable.</div>}
          <div className="nft-note nft-item-caption">{NFT_ITEM_CAPTION}</div>
        </div>
      ) : null}
    </div>
  );
}
