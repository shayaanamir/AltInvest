export default function MarketContextPanel({ detail }) {
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