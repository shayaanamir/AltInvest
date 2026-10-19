import { useState, useEffect } from "react";
import { watchlistApi } from "../services/watchlistApi";
import { IconTrash, IconPlus } from "../components/icons";
import WatchlistSidebar from "../components/watchlists/WatchlistSidebar.jsx";
import WatchlistRow from "../components/watchlists/WatchlistRow.jsx";
import CreateWatchlistModal from "../components/watchlists/CreateWatchlistModal.jsx";
import "../styles/watchlists.css";
import { formatAssetPrice } from "../utils/formatters";
import { ErrorState, useToast } from "../errors";
import AddHoldingModal from "../components/portfolio/AddHoldingModal";
import CreateAlertModal from "../components/alerts/CreateAlertModal";

function formatDate(iso) {
  if (!iso) return "";
  return new Date(iso).toISOString().slice(0, 10);
}

export default function WatchlistsPage() {
  const [lists, setLists] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [searchableItems, setSearchableItems] = useState([]);
  const [addToPortfolio, setAddToPortfolio] = useState(null); // watchlist item being promoted to a holding
  const [alertFor, setAlertFor] = useState(null); // watchlist item an alert is being set on
  const toast = useToast();
  const [activeId, setActiveId] = useState(null);
  const [showModal, setShowModal] = useState(false);

  const emptyState = watchlistApi.getEmptyState();
  const activeList = lists.find((l) => l.id === activeId) || null;

  const refetch = async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const fetched = await watchlistApi.getInitialListsAsync();
      setLists(fetched);
      setActiveId((prev) => (fetched.some((l) => l.id === prev) ? prev : fetched[0]?.id ?? null));
    } catch (e) {
      setLoadError(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Starter assets offered when creating a list (a failure just leaves the picker empty).
    watchlistApi.getSearchableItems().then(setSearchableItems).catch(() => setSearchableItems([]));
    refetch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreate = async (name, chosenDiscoverItems) => {
    let id;
    try {
      ({ id } = await watchlistApi.createList(name));
    } catch (e) {
      toast.error(e, { title: "Couldn't create the watchlist" }); // modal stays open so nothing is lost
      return;
    }

    // Add each chosen starter asset as a real watchlist item
    const failed = [];
    for (const di of chosenDiscoverItems) {
      const type = di.type === "nft" ? "nft" : "crypto";
      const symbolOrSlug = di.type === "nft" ? di.id : di.symbol;
      try {
        await watchlistApi.addItem(id, type, symbolOrSlug);
      } catch {
        failed.push(di.symbol || di.name);
      }
    }
    await refetch();
    setActiveId(id);
    setShowModal(false);
    if (failed.length > 0) {
      toast.error(
        { kind: "partial", detail: `The list was created, but ${failed.join(", ")} could not be added.` },
        { title: "Some assets weren't added" }
      );
    }
  };

  const handleDeleteList = async () => {
    if (!activeList) return;
    try {
      await watchlistApi.deleteList(activeList.id);
    } catch (e) {
      toast.error(e, { title: "Couldn't delete the watchlist" });
      return;
    }
    await refetch();
  };

  const handleRemoveItem = async (item) => {
    try {
      await watchlistApi.removeItem(activeId, item.id);
    } catch (e) {
      toast.error(e, { title: `Couldn't remove ${item.symbol || "that item"}` });
      return;
    }
    // Drop the row once the server confirms
    setLists((prev) =>
      prev.map((l) =>
        l.id === activeId ? { ...l, items: l.items.filter((i) => i.id !== item.id) } : l
      )
    );
  };

  // Promote a watched asset to a holding: opens the add-holding dialog with it already chosen.
  const handleAddToPortfolio = (item) => setAddToPortfolio(item);
  const handleSetAlert = (item) => setAlertFor(item);

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
        ) : loadError ? (
          <div className="sv2-card sv2-card-pad">
            <ErrorState error={loadError} onRetry={refetch} variant="panel" title="Couldn't load your watchlists" />
          </div>
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
                      onSetAlert={handleSetAlert}
                      onRemove={handleRemoveItem}
                    />
                  ))
                )}
              </div>
            )}
          </div>
        )}

        {addToPortfolio && (
          <AddHoldingModal
            initialKind={addToPortfolio.type === "nft" ? "nft" : "crypto"}
            initialAssetId={addToPortfolio.id}
            onClose={() => setAddToPortfolio(null)}
          />
        )}
        {alertFor && (
          <CreateAlertModal
            target={
              alertFor.type === "nft"
                ? { type: "nft", slug: alertFor.id, name: alertFor.name }
                : { type: "crypto", symbol: alertFor.symbol, name: alertFor.name }
            }
            hint={alertFor.price != null ? `Currently ${formatAssetPrice(alertFor.price)}` : undefined}
            onClose={() => setAlertFor(null)}
          />
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