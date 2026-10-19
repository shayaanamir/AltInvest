import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { describeError } from "./errorCatalog";
import { onReportedError } from "./errorBus";
import "./errors.css";

const ToastContext = createContext(null);
const AUTO_DISMISS_MS = 7000;
const DEDUPE_MS = 3000;
const MAX_VISIBLE = 4;

/**
 * Popups for something the person just tried that failed (save, delete, refresh…).
 *   const toast = useToast();
 *   toast.error(err, { title: "Couldn't save profile" });
 *   toast.success("Alert created.");
 * Also shows anything sent through errorBus.reportError() and any unhandled promise rejection.
 */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const lastShown = useRef(new Map()); // message -> timestamp, to collapse repeats
  const nextId = useRef(1);

  const dismiss = useCallback((id) => setToasts((t) => t.filter((x) => x.id !== id)), []);

  const error = useCallback((err, { title } = {}) => {
    const info = describeError(err);
    if (info.kind === "auth") return; // the session-expired modal already handles this
    const text = info.message;
    const now = Date.now();
    if (now - (lastShown.current.get(text) || 0) < DEDUPE_MS) return;
    lastShown.current.set(text, now);

    const id = nextId.current++;
    setToasts((t) => [...t.slice(-(MAX_VISIBLE - 1)), { id, title: title || info.title, message: text }]);
    setTimeout(() => dismiss(id), AUTO_DISMISS_MS);
  }, [dismiss]);

  // Confirmation that something the person asked for went through (not an error).
  const success = useCallback((message, { title } = {}) => {
    const id = nextId.current++;
    setToasts((t) => [...t.slice(-(MAX_VISIBLE - 1)), { id, title: title || "Done", message, ok: true }]);
    setTimeout(() => dismiss(id), AUTO_DISMISS_MS);
  }, [dismiss]);

  useEffect(() => onReportedError((err, options) => error(err, options)), [error]);

  // Anything that rejects with nobody catching it would otherwise vanish into the console.
  useEffect(() => {
    const handler = (event) => {
      if (event.reason?.name === "AbortError") return;
      console.error("Unhandled rejection:", event.reason);
      error(event.reason);
    };
    window.addEventListener("unhandledrejection", handler);
    return () => window.removeEventListener("unhandledrejection", handler);
  }, [error]);

  const value = useMemo(() => ({ error, success }), [error, success]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="err-toasts" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`err-toast${t.ok ? " ok" : ""}`} role={t.ok ? "status" : "alert"}>
            <div>
              <div className="err-toast-title">{t.title}</div>
              <div>{t.message}</div>
            </div>
            <button type="button" className="err-toast-close" aria-label="Dismiss" onClick={() => dismiss(t.id)}>×</button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside <ToastProvider>");
  return ctx;
}
