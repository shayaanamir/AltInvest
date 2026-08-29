import { useState, useEffect } from "react";
import { watchlistApi } from "../services/watchlistApi";
import { USE_MOCK } from "../config";
import { IconTrash, IconPlus } from "../components/icons";
import WatchlistSidebar from "../components/watchlists/WatchlistSidebar.jsx";
import WatchlistRow from "../components/watchlists/WatchlistRow.jsx";
import CreateWatchlistModal from "../components/watchlists/CreateWatchlistModal.jsx";
import "../styles/watchlists.css";

function formatDate(iso) {
  if (!iso) return "";
  return new Date(iso).toISOString().slice(0, 10);
}

export default function WatchlistsPage() {
  const [lists, setLists] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeId, setActiveId] = useState(null);
  const [showModal, setShowModal] = useState(false);

  const emptyState = watchlistApi.getEmptyState();
  const searchableItems = watchlistApi.getSearchableItems();
  const activeList = lists.find((l) => l.id === activeId) || null;

  const refetch = async () => {
    setLoading(true);
    const fetched = await watchlistApi.getInitialListsAsync();
    setLists(fetched);
    setActiveId((prev) => (fetched.some((l) => l.id === prev) ? prev : fetched[0]?.id ?? null));
    setLoading(false);
  };

  useEffect(() => {
    refetch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreate = async (name, chosenDiscoverItems) => {
    if (USE_MOCK) {
      const newList = {
        id: `wl_${Date.now()}`,
        name,
        createdAt: new Date().toISOString(),
        items: chosenDiscoverItems.map((di) => watchlistApi.buildListItemFromDiscoverItem(di)),
      };
      setLists((prev) => [...prev, newList]);
      setActiveId(newList.id);
      setShowModal(false);
      return;
    }

    const { id } = await watchlistApi.createList(name);
    // Add each chosen starter asset as a real watchlist item
    for (const di of chosenDiscoverItems) {
      const type = di.type === "nft" ? "nft" : "crypto";
      const symbolOrSlug = di.type === "nft" ? di.id : di.symbol;
      await watchlistApi.addItem(id, type, symbolOrSlug);
    }
    await refetch();
    setActiveId(id);
    setShowModal(false);
  };

  const handleDeleteList = async () => {
    if (!activeList) return;
    if (USE_MOCK) {
      const remaining = lists.filter((l) => l.id !== activeList.id);
      setLists(remaining);
      setActiveId(remaining[0]?.id ?? null);
      return;
    }
    await watchlistApi.deleteList(activeList.id);
    await refetch();
  };

  const handleRemoveItem = async (item) => {
    if (USE_MOCK) {
      setLists((prev) =>
        prev.map((l) =>
          l.id === activeId ? { ...l, items: l.items.filter((i) => i.id !== item.id) } : l
        )
      );
      return;
    }
    await watchlistApi.removeItem(activeId, item.id);
    // Optimistic local update so the row disappears immediately
    setLists((prev) =>
      prev.map((l) =>
        l.id === activeId ? { ...l, items: l.items.filter((i) => i.id !== item.id) } : l
      )
    );
  };

  const handleAddToPortfolio = (item) => {
    // Portfolio holdings creation lives in portfolioApi.addHolding — wire
    // this to a real "add holding" modal when one exists. For now this is
    // the integration point.
    console.log("Add to portfolio requested:", item);
  };

  return (
    <div className="sv2">
      <div className="sv2-page wl-page">
        <div className="wl-header">
          <div>
            <h1 className="wl-title">Watchlists</h1>
            <p className="wl-sub">Track assets without owning them — promote to Portfolio when you commit.</p>
          </div>
          <button className="wl-new-btn" onClick={() => setShowModal(true)}>
            <IconPlus size={14} />
            New watchlist
          </button>
        </div>

        {loading ? (
          <div className="sv2-muted sv2-small">Loading watchlists…</div>
        ) : lists.length === 0 ? (
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
                    <IconTrash size={14} />
                    Delete list
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
    </div>
  );
}