/**
 * Bookkeeping for useAsync: only the newest request may update state, and a "silent" refresh never
 * leaves the hook stuck in loading (audit G-24).
 *
 * The bug it fixes: a silent re-fetch (from a subscription) cancelled a normal load that was still
 * in flight. The cancelled load never cleared `loading`, and the silent one isn't allowed to, so the
 * spinner stayed forever. Now a silent request that supersedes a pending normal load takes over that
 * load: it is treated as a normal request, so it clears `loading` (and reports its error) when done.
 */
export function createLatestRequest() {
  let current = null;
  let loadPending = false; // a normal (non-silent) request was started and hasn't settled yet

  return {
    /** Starts a request, cancelling the previous one. Returns its handle; `handle.silent` is the effective mode. */
    start(silent = false) {
      const effectiveSilent = Boolean(silent) && !loadPending;
      if (current) current.cancelled = true;
      const handle = { silent: effectiveSilent, cancelled: false };
      if (!effectiveSilent) loadPending = true;
      current = handle;
      return handle;
    },

    /** Call when the request settles. Returns true if its result should be applied. */
    settle(handle) {
      if (handle.cancelled) return false;
      if (!handle.silent) loadPending = false;
      return true;
    },

    /** Cancels a request (effect cleanup, unmount). */
    cancel(handle) {
      handle.cancelled = true;
      if (current === handle) {
        current = null;
        loadPending = false;
      }
    },
  };
}
