import { useState, useEffect, useCallback, useRef } from "react";

/**
 * Replaces the repeated:
 *   const [x, setX] = useState(null);
 *   useEffect(() => { api.get().then(setX).catch(console.error); }, [deps]);
 * pattern found across components.
 *
 * Usage:
 *   const { data, loading, error, refetch } = useAsync(() => sentimentApi.getMoodOverview(), []);
 */
export function useAsync(asyncFn, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const fnRef = useRef(asyncFn);
  fnRef.current = asyncFn;

  const run = useCallback(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fnRef.current()
      .then((result) => { if (!cancelled) setData(result); })
      .catch((err) => { if (!cancelled) { console.error(err); setError(err); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => run(), [run]);

  return { data, loading, error, refetch: run, setData };
}

