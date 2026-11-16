const signedPct = (v, digits = 2) => (v != null ? `${v >= 0 ? "+" : ""}${Number(v).toFixed(digits)}%` : "—");

// NFT collections: floor moves and sales pace (the inputs of the NFT market signal), not the crypto
// volume / trending / BTC dominance figures, which do not exist for a collection.
function NftMarketContext({ detail }) {
  const s = detail.marketSignals || {};
  const q = detail.dataQuality || {};
  return (
    <div className="sv2-card sv2-card-pad">
      <div className="sv2-card-title">Market context</div>
      <div className="sv2-card-sub sv2-mb-16">How the floor and sales compare with the mood.</div>
      {q.marketFallback && (
        <div className="sv2-small sv2-muted sv2-mb-16">
          No recent floor data was stored for this collection, so this read is from the news alone.
        </div>
      )}
      <div className="sv2-stat-grid">
        <div>
          <div className="sv2-stat-label">24h floor change</div>
          <div className={`sv2-stat-value ${(s.priceChange24h ?? 0) >= 0 ? "positive" : "negative"}`}>{signedPct(s.priceChange24h)}</div>
        </div>
        <div>
          <div className="sv2-stat-label">7d floor change</div>
          <div className={`sv2-stat-value ${(s.priceChange7d ?? 0) >= 0 ? "positive" : "negative"}`}>{signedPct(s.priceChange7d)}</div>
        </div>
        <div>
          <div className="sv2-stat-label">Sales pace vs 30 days</div>
          <div className="sv2-stat-value">{s.activityRatio != null ? `${Number(s.activityRatio).toFixed(2)}×` : "—"}</div>
        </div>
        <div>
          <div className="sv2-stat-label">Floor as of</div>
          <div className="sv2-stat-value">{s.asOf || "—"}</div>
        </div>
      </div>
      {detail.validationNote && <div className="sv2-small sv2-muted sv2-mt-12">{detail.validationNote}{detail.scorer ? ` Scored by ${detail.scorer}.` : ""}</div>}
    </div>
  );
}

export default function MarketContextPanel({ detail }) {
  if (detail?.category === "nft") return <NftMarketContext detail={detail} />;
  const s = detail?.marketSignals || {};
  const q = detail?.dataQuality || {};
  const notice = q.cmcKeyMissing
    ? "Market data is off: no CoinMarketCap API key is configured, so the market half of this read is a neutral placeholder."
    : q.cmcFallback
      ? "CoinMarketCap couldn't be reached for part of this read, so that part is a neutral placeholder. Missing figures are shown as —."
      : null;
  return (
    <div className="sv2-card sv2-card-pad">
      <div className="sv2-card-title">Market context</div>
      <div className="sv2-card-sub sv2-mb-16">How the tape compares with the mood.</div>
      {notice && <div className="sv2-small sv2-muted sv2-mb-16">{notice}</div>}

      <div className="sv2-stat-grid">
        <div>
          <div className="sv2-stat-label">24h price change</div>
          <div className={`sv2-stat-value ${(s.priceChange24h ?? 0) >= 0 ? "positive" : "negative"}`}>
            {s.priceChange24h != null ? `${s.priceChange24h >= 0 ? "+" : ""}${Number(s.priceChange24h).toFixed(2)}%` : "—"}
          </div>
        </div>
        <div>
          <div className="sv2-stat-label">24h volume change</div>
          <div className={`sv2-stat-value ${(s.volumeChange24h ?? 0) >= 0 ? "positive" : "negative"}`}>
            {s.volumeChange24h != null ? `${s.volumeChange24h >= 0 ? "+" : ""}${Number(s.volumeChange24h).toFixed(1)}%` : "—"}
          </div>
        </div>
        <div>
          <div className="sv2-stat-label">Trending</div>
          <div className="sv2-stat-value">{s.isTrending == null ? "—" : s.isTrending ? "Yes" : "No"}</div>
        </div>
        <div>
          <div className="sv2-stat-label">BTC dominance</div>
          <div className="sv2-stat-value">{s.btcDominance != null ? `${Number(s.btcDominance).toFixed(1)}%` : "—"}</div>
        </div>
      </div>
    </div>
  );
}