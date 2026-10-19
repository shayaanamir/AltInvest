// frontend/src/errors/errorBus.js
// Lets non-React code (services, event handlers, window listeners) raise a user-visible
// error without importing React. ToastProvider subscribes and renders it.
const target = new EventTarget();

/** reportError(err, { title }) — shows a toast. Safe to call from anywhere. */
export function reportError(err, options = {}) {
  target.dispatchEvent(new CustomEvent("error", { detail: { err, options } }));
}

export function onReportedError(handler) {
  const listener = (e) => handler(e.detail.err, e.detail.options);
  target.addEventListener("error", listener);
  return () => target.removeEventListener("error", listener);
}
