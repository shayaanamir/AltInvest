import { useState, useEffect } from "react";
import { watchlistApi } from "../services/watchlistApi";
import { IconTrash, IconPlus, IconPencil } from "../components/icons";
import WatchlistSidebar from "../components/watchlists/WatchlistSidebar.jsx";
import WatchlistRow from "../components/watchlists/WatchlistRow.jsx";
import CreateWatchlistModal from "../components/watchlists/CreateWatchlistModal.jsx";
import AddToWatchlistModal from "../components/watchlists/AddToWatchlistModal.jsx";
import "../styles/watchlists.css";
import { formatAssetPrice } from "../utils/formatters";
import { ErrorState, useToast, describeError } from "../errors";
import { formatDate, useAppPreferences } from "../services/appPreferences";
import AddHoldingModal from "../components/portfolio/AddHoldingModal";
import CreateAlertModal from "../components/alerts/CreateAlertModal";

export default function WatchlistsPage() {
  useAppPreferences(); // re-render when the date format changes
  const [lists, setLists] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [searchableItems, setSearchableItems] = useState([]);
  const [addToPortfolio, setAddToPortfolio] = useState(null); // watchlist item being promoted to a holding
  const [alertFor, setAlertFor] = useState(null); // watchlist item an alert is being set on
  const toast = useToast();
  const [activeId, setActiveId] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [addingItems, setAddingItems] = useState(false); // "Add assets" dialog for the open list
  const [renaming, setRenaming] = useState(null); // draft name while renaming the open list

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

  // One request creates the list with its starter assets, so it can't half-succeed. A failure is
  // thrown back to the dialog, which shows it and stays open.
  const handleCreate = async (name, chosenDiscoverItems) => {
    let id;
    try {
      ({ id } = await watchlistApi.createList(
        name,
        chosenDiscoverItems.map((di) => ({
          type: di.type === "nft" ? "nft" : "crypto",
          symbolOrSlug: di.type === "nft" ? di.id : di.symbol,
        }))
      ));
    } catch (e) {
      throw new Error(describeError(e).message, { cause: e });
    }
    await refetch();
    setActiveId(id);
    setShowModal(false);
    toast.success(`"${name}" was created.`, { title: "Watchlist created" });
  };

  const handleDeleteList = async () => {
    if (!activeList) return;
    const count = activeList.items.length;
    if (!window.confirm(`Delete "${activeList.name}"${count ? ` and the ${count} asset${count === 1 ? "" : "s"} on it` : ""}? This can't be undone.`)) return;
    try {
      await watchlistApi.deleteList(activeList.id);
    } catch (e) {
      toast.error(e, { title: "Couldn't delete the watchlist" });
      return;
    }
    await refetch();
  };

  const saveRename = async () => {
    const name = (renaming || "").trim();
    if (!activeList || !name || name === activeList.name) {
      setRenaming(null);
      return;
    }
    try {
      await watchlistApi.renameList(activeList.id, name);
    } catch (e) {
      toast.error(e, { title: "Couldn't rename the watchlist" });
      return; // keep the field open with what was typed
    }
    setLists((prev) => prev.map((l) => (l.id === activeList.id ? { ...l, name } : l)));
    setRenaming(null);
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
                    {renaming != null ? (
                      <form className="wl-rename" onSubmit={(e) => { e.preventDefault(); saveRename(); }}>
                        <input
                          className="wl-modal-input wl-rename-input"
                          value={renaming}
                          maxLength={60}
                          autoFocus
                          aria-label="Watchlist name"
                          onChange={(e) => setRenaming(e.target.value)}
                          onKeyDown={(e) => e.key === "Escape" && setRenaming(null)}
                        />
                        <button type="submit" className="wl-modal-create" disabled={!renaming.trim()}>Save</button>
                        <button type="button" className="wl-modal-cancel" onClick={() => setRenaming(null)}>Cancel</button>
                      </form>
                    ) : (
                      <h2 className="wl-panel-title wl-title-row">
                        {activeList.name}
                        <button type="button" className="wl-icon-btn" title="Rename" aria-label="Rename watchlist" onClick={() => setRenaming(activeList.name)}>
                          <IconPencil size={13} />
                        </button>
                      </h2>
                    )}
                    <p className="wl-panel-sub">
                      {activeList.items.length} assets · created {formatDate(activeList.createdAt)}
                    </p>
                  </div>
                  <div className="wl-panel-actions">
                    <button className="wl-delete-btn wl-add-btn" onClick={() => setAddingItems(true)}>
                      <IconPlus size={14} />
                      Add assets
                    </button>
                    <button className="wl-delete-btn" onClick={handleDeleteList}>
                      <IconTrash size={14} />
                      Delete list
                    </button>
                  </div>
                </div>

                {activeList.items.length === 0 ? (
                  <div className="wl-empty-items">
                    <h3>Nothing here yet</h3>
                    <p>Use "Add assets" above, or the star on Discover and any asset page.</p>
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

        {addingItems && activeList && (
          <AddToWatchlistModal
            list={activeList}
            searchableItems={searchableItems}
            onClose={() => {
              setAddingItems(false);
              refetch();
            }}
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