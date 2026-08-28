import { IconStar } from "../icons";

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
            <IconStar size={15} filled={l.id === activeId} />
            {l.name}
          </span>
          <span className="wl-side-count">{l.items.length}</span>
        </div>
      ))}
    </div>
  );
}