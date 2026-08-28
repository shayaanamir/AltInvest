export default function WatchlistSidebar({ lists, activeId, onSelect }) {
  return (
    <div className="wl-sidebar">
      {lists.map((l) => (
        <div
          key={l.id}
          className={`wl-side-item ${l.id === activeId ? "active" : ""}`}
          onClick={() => onSelect(l.id)}
        >
          <span className="wl-side-item-name">
            <svg width="15" height="15" viewBox="0 0 24 24" fill={l.id === activeId ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.8">
              <path d="M12 2.5l2.9 6.4 6.9.7-5.2 4.7 1.5 6.9L12 17.6l-6.1 3.6 1.5-6.9-5.2-4.7 6.9-.7z" />
            </svg>
            {l.name}
          </span>
          <span className="wl-side-count">{l.items.length}</span>
        </div>
      ))}
    </div>
  );
}