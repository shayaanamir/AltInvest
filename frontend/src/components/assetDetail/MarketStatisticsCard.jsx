export default function MarketStatisticsCard({ marketStats }) {
  if (!marketStats || marketStats.length === 0) return null;

  return (
    <div className="sv2-card adt-stats-card">
      <div className="sv2-card-title adt-stats-title">Market statistics</div>
      <div className="adt-stats-grid">
        {marketStats.map((s, i) => (
          <div
            key={s.label}
            className="adt-stat-cell"
            style={{ borderRight: i < marketStats.length - 1 ? "1px solid var(--sv2-border)" : "none" }}
          >
            <div className="adt-stat-label">{s.label.toUpperCase()}</div>
            <div className="adt-stat-value">{s.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}