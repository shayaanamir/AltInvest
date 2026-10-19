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
