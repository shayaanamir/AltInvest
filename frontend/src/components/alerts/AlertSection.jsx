export default function AlertSection({ title, subtitle, count, children }) {
  return (
    <div className="alr-card">
      <div className="alr-section-head">
        <span className="alr-section-title">{title}</span>
        <span className="alr-count-badge">{count}</span>
      </div>
      <p className="alr-section-sub">{subtitle}</p>
      <div className="alr-list">
        {count === 0 ? (
          <div className="alr-empty">Nothing here right now.</div>
        ) : (
          children
        )}
      </div>
    </div>
  );
}