// frontend/src/errors/connectionStatus.js
// Tracks whether the API is reachable, so a *persistent* condition shows as one banner
// instead of a dozen cards each saying "failed". apiClient reports every request outcome here.
let apiReachable = true;
const target = new EventTarget();

export function reportApiReachable(ok) {
  if (ok === apiReachable) return;
  apiReachable = ok;
  target.dispatchEvent(new Event("change"));
}

export function isApiReachable() {
  return apiReachable;
}

export function subscribeConnection(handler) {
  target.addEventListener("change", handler);
  return () => target.removeEventListener("change", handler);
}
