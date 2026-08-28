import { useState } from "react";
import { watchlistApi } from "../services/watchlistApi";
import WatchlistSidebar from "../components/watchlists/WatchlistSidebar.jsx";
import WatchlistRow from "../components/watchlists/WatchlistRow.jsx";
import CreateWatchlistModal from "../components/watchlists/CreateWatchlistModal.jsx";
import "../styles/watchlists.css";

function formatDate(iso) {
  if (!iso) return "";
  return new Date(iso).toISOString().slice(0, 10);
}

export default function WatchlistsPage() {
  const [lists, setLists] = useState(() => watchlistApi.getInitialLists());
  const [activeId, setActiveId] = useState(() => lists[0]?.id ?? null);
  const [showModal, setShowModal] = useState(false);

  const emptyState = watchlistApi.getEmptyState();
  const searchableItems = watchlistApi.getSearchableItems();
  const activeList = lists.find((l) => l.id === activeId) || null;

  const handleCreate = (name, chosenDiscoverItems) => {
    const newList = {
      id: `wl_${Date.now()}`,
      name,
      createdAt: new Date().toISOString(),
      items: chosenDiscoverItems.map((di) => watchlistApi.buildListItemFromDiscoverItem(di)),
    };
    setLists((prev) => [...prev, newList]);
    setActiveId(newList.id);
    setShowModal(false);
  };

  const handleDeleteList = () => {
    if (!activeList) return;
    const remaining = lists.filter((l) => l.id !== activeList.id);
    setLists(remaining);
    setActiveId(remaining[0]?.id ?? null);
  };

  const handleRemoveItem = (item) => {
    setLists((prev) =>
      prev.map((l) =>
        l.id === activeId ? { ...l, items: l.items.filter((i) => i.id !== item.id) } : l
      )
    );
  };

  const handleAddToPortfolio = (item) => {
    // Portfolio holdings live on the Portfolio page's own data model —
    // this is the integration point for wiring that up.
    console.log("Add to portfolio requested:", item);
  };

  return (
    <div className="wl-page">
      <div className="wl-header">
        <div>
          <h1 className="wl-title">Watchlists</h1>
          <p className="wl-sub">Track assets without owning them — promote to Portfolio when you commit.</p>
        </div>
        <button className="wl-new-btn" onClick={() => setShowModal(true)}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><path d="M12 5v14M5 12h14" /></svg>
          New watchlist
        </button>
      </div>

      {lists.length === 0 ? (
        <div className="wl-empty-lists">
          <h3>{emptyState.title}</h3>
          <p>{emptyState.subtitle}</p>
          <button className="wl-new-btn" style={{ margin: "0 auto" }} onClick={() => setShowModal(true)}>
            {emptyState.cta}
          </button>
        </div>
      ) : (
        <div className="wl-layout">
          <WatchlistSidebar lists={lists} activeId={activeId} onSelect={setActiveId} />

          {activeList && (
            <div className="wl-panel">
              <div className="wl-panel-head">
                <div>
                  <h2 className="wl-panel-title">{activeList.name}</h2>
                  <p className="wl-panel-sub">
                    {activeList.items.length} assets · created {formatDate(activeList.createdAt)}
                  </p>
                </div>
                <button className="wl-delete-btn" onClick={handleDeleteList}>
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" className="bi bi-trash" viewBox="0 0 16 16">
                    <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0z"/>
                    <path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4zM2.5 3h11V2h-11z"/>
                  </svg>
                  Delete lists
                </button>
              </div>

              {activeList.items.length === 0 ? (
                <div className="wl-empty-items">
                  <h3>Nothing here yet</h3>
                  <p>Add assets from Discover or any asset page to start tracking them.</p>
                </div>
              ) : (
                activeList.items.map((item) => (
                  <WatchlistRow
                    key={item.id}
                    item={item}
                    onAddToPortfolio={handleAddToPortfolio}
                    onRemove={handleRemoveItem}
                  />
                ))
              )}
            </div>
          )}
        </div>
      )}

      {showModal && (
        <CreateWatchlistModal
          searchableItems={searchableItems}
          onCancel={() => setShowModal(false)}
          onCreate={handleCreate}
        />
      )}
    </div>
  );
}