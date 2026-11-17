import { createContext, useContext } from "react";

// The toast context and its hook. The provider component is in ToastProvider.jsx.
export const ToastContext = createContext(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside <ToastProvider>");
  return ctx;
}
