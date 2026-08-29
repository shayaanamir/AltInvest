// frontend/src/hooks/sessionEvents.js
// Minimal event bus so apiClient.js (not a React module) can notify the
// app shell when a request comes back 401, without importing React state.
const target = new EventTarget();
const SESSION_EXPIRED = "session-expired";

export function emitSessionExpired() {
    target.dispatchEvent(new Event(SESSION_EXPIRED));
}

export function onSessionExpired(handler) {
    target.addEventListener(SESSION_EXPIRED, handler);
    return () => target.removeEventListener(SESSION_EXPIRED, handler);
}