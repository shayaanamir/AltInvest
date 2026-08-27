export default function MarketContextPanel({ detail }) {
  const s = detail.marketSignals;
  return (
    <div className="sv2-card sv2-card-pad">
      <div className="sv2-card-title">Market context</div>
      <div className="sv2-card-sub sv2-mb-16">How the tape compares with the mood.</div>

      <div className="sv2-stat-grid">
        <div>
          <div className="sv2-stat-label">24h price change</div>
          <div className={`sv2-stat-value ${s.priceChange24h >= 0 ? "positive" : "negative"}`}>
            {s.priceChange24h >= 0 ? "+" : ""}{s.priceChange24h.toFixed(2)}%
          </div>
        </div>
        <div>
          <div className="sv2-stat-label">24h volume change</div>
          <div className={`sv2-stat-value ${s.volumeChange24h >= 0 ? "positive" : "negative"}`}>
            {s.volumeChange24h >= 0 ? "+" : ""}{s.volumeChange24h.toFixed(1)}%
          </div>
        </div>
        <div>
          <div className="sv2-stat-label">Trending</div>
          <div className="sv2-stat-value">{s.isTrending ? "Yes — rank 2" : "No"}</div>
        </div>
        <div>
          <div className="sv2-stat-label">BTC dominance</div>
          <div className="sv2-stat-value">{s.btcDominance.toFixed(1)}%</div>
        </div>
      </div>
    </div>
  );
}