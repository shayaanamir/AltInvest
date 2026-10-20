import { useState, useEffect, useCallback, useRef } from "react";

/**
 * Replaces the repeated:
 *   const [x, setX] = useState(null);
 *   useEffect(() => { api.get().then(setX).catch(console.error); }, [deps]);
 * pattern found across components.
 *
 * Usage:
 *   const { data, loading, error, refetch } = useAsync(() => sentimentApi.getMoodOverview(), []);
 *
 * Optional third argument: { subscribe } — a function (handler) => unsubscribe. The hook re-fetches
 * whenever the subscription fires, e.g. { subscribe: onHoldingsChanged }. Those re-fetches are
 * silent: the current data stays on screen (no loading state), and a failed one leaves it as it
 * was instead of replacing it with an error. Only an explicit refetch() or a change of deps
 * shows loading and errors.
 */
export function useAsync(asyncFn, deps = [], { subscribe } = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const fnRef = useRef(asyncFn);
  fnRef.current = asyncFn;

  const cancelPrevRef = useRef(null);

  const run = useCallback((silent = false) => {
    cancelPrevRef.current?.(); // a newer request supersedes one still in flight
    let cancelled = false;
    if (!silent) {
      setLoading(true);
      setError(null);
    }
    fnRef.current()
      .then((result) => { if (!cancelled) { setData(result); if (silent) setError(null); } })
      .catch((err) => { if (!cancelled) { console.error(err); if (!silent) setError(err); } })
      .finally(() => { if (!cancelled && !silent) setLoading(false); });
    const cancel = () => { cancelled = true; };
    cancelPrevRef.current = cancel;
    return cancel;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => run(), [run]);

  useEffect(() => {
    if (!subscribe) return undefined;
    return subscribe(() => run(true));
  }, [subscribe, run]);

  // A wrapper, so an event object handed over by onClick={refetch} isn't read as `silent`.
  const refetch = useCallback(() => run(false), [run]);

  return { data, loading, error, refetch, setData };
}

