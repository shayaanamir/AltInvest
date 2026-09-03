import { useEffect, useRef, useCallback } from "react";
import { USE_MOCK, API_BASE_URL } from "../config";

/**
 * useSentimentPoller
 *
 * Polls GET /sentiment every POLL_INTERVAL_MS and calls onUpdate() only when
 * the backend has produced NEW data — detected by comparing the newest
 * `last_updated` / `timestamp` field across all assets.
 *
 * Design choices:
 *  - 5-min poll interval: the backend serves from MongoDB cache, so each poll
 *    is a cheap DB read — no pipeline run triggered.
 *  - Page Visibility API: pauses polling while the tab is hidden; resumes and
 *    polls immediately when the tab becomes visible again.
 *  - Startup jitter: first poll is offset by a random 0-10 s so multiple
 *    open tabs don't all hit the server at the same second.
 *  - No-op in mock mode: nothing changes server-side, so polling would be pointless.
 */

const POLL_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

/** Returns the most recent timestamp string from the /sentiment response. */
function newestTimestamp(items) {
  if (!Array.isArray(items) || !items.length) return null;
  return (
    items
      .map((r) => r.last_updated ?? r.timestamp ?? "")
      .filter(Boolean)
      .sort()
      .at(-1) ?? null
  );
}

/**
 * @param {object}   opts
 * @param {function} opts.onUpdate  - Called when fresh data has arrived
 * @param {boolean}  [opts.enabled] - Set false to disable (e.g. when mock)
 */
export function useSentimentPoller({ onUpdate, enabled = true } = {}) {
  const lastSeenRef   = useRef(null);
  const timerRef      = useRef(null);
  const onUpdateRef   = useRef(onUpdate);
  onUpdateRef.current = onUpdate;

  const poll = useCallback(async () => {
    if (USE_MOCK || !enabled) return;
    try {
      const res = await fetch(`${API_BASE_URL}/sentiment`, {
        signal: AbortSignal.timeout(10_000),
      });
      if (!res.ok) return;

      const data    = await res.json();
      const newest  = newestTimestamp(data);

      if (newest && newest !== lastSeenRef.current) {
        lastSeenRef.current = newest;
        onUpdateRef.current?.();
      }
    } catch {
      // Swallow — network/timeout errors are non-fatal for a poller
    }
  }, [enabled]);

  useEffect(() => {
    if (USE_MOCK || !enabled) return;

    // Random 0-10 s jitter on first poll so tabs don't sync up
    const jitter = Math.random() * 10_000;

    const schedule = () => {
      timerRef.current = setTimeout(async () => {
        if (document.visibilityState !== "hidden") {
          await poll();
        }
        schedule();
      }, POLL_INTERVAL_MS);
    };

    const firstTimer = setTimeout(() => {
      poll();
      schedule();
    }, jitter);

    // When tab becomes visible again, poll immediately to catch missed updates
    const onVisibility = () => {
      if (document.visibilityState === "visible") poll();
    };
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      clearTimeout(firstTimer);
      clearTimeout(timerRef.current);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [poll, enabled]);
}
