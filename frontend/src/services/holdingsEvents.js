// frontend/src/services/holdingsEvents.js
// Tiny event bus: portfolioApi announces that holdings changed (added / edited / removed), and any
// screen showing portfolio-derived numbers re-fetches. Pass `onHoldingsChanged` as useAsync's
// `subscribe` option.
const target = new EventTarget();

export function notifyHoldingsChanged() {
  target.dispatchEvent(new Event("changed"));
}

export function onHoldingsChanged(handler) {
  target.addEventListener("changed", handler);
  return () => target.removeEventListener("changed", handler);
}

// Same idea for watchlists: raised after a list or one of its items is created / changed / removed.
const watchlistTarget = new EventTarget();

export function notifyWatchlistsChanged() {
  watchlistTarget.dispatchEvent(new Event("changed"));
}

export function onWatchlistsChanged(handler) {
  watchlistTarget.addEventListener("changed", handler);
  return () => watchlistTarget.removeEventListener("changed", handler);
}
