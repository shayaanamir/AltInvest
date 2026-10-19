import { useEffect, useState } from "react";
import systemStates from "../content/systemStates.json";
import { isApiReachable, subscribeConnection } from "./connectionStatus";
import "./errors.css";

/**
 * Persistent banner for app-wide conditions: browser offline, or the API unreachable.
 * Clears itself as soon as a request succeeds again.
 */
export default function ConnectionBanner() {
  const [online, setOnline] = useState(() => navigator.onLine);
  const [apiUp, setApiUp] = useState(isApiReachable);

  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    const unsub = subscribeConnection(() => setApiUp(isApiReachable()));
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
      unsub();
    };
  }, []);

  if (online && apiUp) return null;

  return (
    <div className="err-banner" role="status">
      <strong>{online ? "Can't reach the server." : "You're offline."}</strong>
      <span>
        {online
          ? "Some data may be missing or out of date. Use Retry on a section, or reload."
          : systemStates.networkOffline.message}
      </span>
      <button type="button" className="err-btn" onClick={() => window.location.reload()}>Reload</button>
    </div>
  );
}
