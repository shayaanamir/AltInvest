import { useState, useRef, useCallback, useEffect } from "react";

/**
 * Generic open/close controller for popovers and dropdowns.
 * Closes on outside click and on Escape. Returns a ref to attach
 * to the trigger + panel's shared container.
 */
export function useDisclosure(initialOpen = false) {
  const [isOpen, setIsOpen] = useState(initialOpen);
  const ref = useRef(null);

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);

  useEffect(() => {
    if (!isOpen) return;

    function handlePointerDown(event) {
      if (ref.current && !ref.current.contains(event.target)) close();
    }
    function handleKeyDown(event) {
      if (event.key === "Escape") close();
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, close]);

  return { isOpen, open, close, toggle, ref };
}