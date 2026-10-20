// frontend/src/errors/connectionStatus.js
// Tracks whether the API is reachable, so a *persistent* condition shows as one banner
// instead of a dozen cards each saying "failed". apiClient reports every request outcome here.
//
// The state starts as "unknown": nothing has been asked yet, so nothing can be called live or
// down. It only becomes "up" after a request succeeds and "down" after one fails to connect.
let state = "unknown"; // "unknown" | "up" | "down"
const target = new EventTarget();

export function reportApiReachable(ok) {
  const next = ok ? "up" : "down";
  if (next === state) return;
  state = next;
  target.dispatchEvent(new Event("change"));
}

/** "unknown" until the first request settles, then "up" or "down". */
export function getApiState() {
  return state;
}

/** False only once a request has actually failed — "unknown" doesn't raise the offline banner. */
export function isApiReachable() {
  return state !== "down";
}

export function subscribeConnection(handler) {
  target.addEventListener("change", handler);
  return () => target.removeEventListener("change", handler);
}
