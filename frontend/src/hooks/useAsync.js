import { useState, useEffect, useCallback, useRef } from "react";
import { createLatestRequest } from "../utils/latestRequest.js";

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

  const requestsRef = useRef(null);
  if (requestsRef.current === null) requestsRef.current = createLatestRequest();

  const run = useCallback((silent = false) => {
    const requests = requestsRef.current;
    // A newer request supersedes one still in flight. A silent one that supersedes a pending normal
    // load is promoted to a normal one, so loading still ends (utils/latestRequest.js, audit G-24).
    const req = requests.start(silent);
    if (!req.silent) {
      setLoading(true);
      setError(null);
    }
    fnRef.current()
      .then((result) => {
        if (!requests.settle(req)) return;
        setData(result);
        setError(null);
        if (!req.silent) setLoading(false);
      })
      .catch((err) => {
        if (!requests.settle(req)) return;
        console.error(err);
        if (!req.silent) {
          setError(err);
          setLoading(false);
        }
      });
    return () => requests.cancel(req);
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

