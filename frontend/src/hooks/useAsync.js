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
 * whenever the subscription fires, e.g. { subscribe: onHoldingsChanged }.
 */
export function useAsync(asyncFn, deps = [], { subscribe } = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const fnRef = useRef(asyncFn);
  fnRef.current = asyncFn;

  const cancelPrevRef = useRef(null);

  const run = useCallback(() => {
    cancelPrevRef.current?.(); // a newer request supersedes one still in flight
    let cancelled = false;
    setLoading(true);
    setError(null);
    fnRef.current()
      .then((result) => { if (!cancelled) setData(result); })
      .catch((err) => { if (!cancelled) { console.error(err); setError(err); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    const cancel = () => { cancelled = true; };
    cancelPrevRef.current = cancel;
    return cancel;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => run(), [run]);

  useEffect(() => {
    if (!subscribe) return undefined;
    return subscribe(() => run());
  }, [subscribe, run]);

  return { data, loading, error, refetch: run, setData };
}

