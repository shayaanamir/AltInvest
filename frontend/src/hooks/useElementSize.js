import { useState, useEffect, useRef } from "react";

export function useElementSize(defaultDims = { W: 0, H: 0 }) {
  const ref = useRef(null);
  const [dims, setDims] = useState(defaultDims);

  useEffect(() => {
    if (!ref.current) return;
    const ob = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        const W = Math.round(entry.contentRect.width);
        const H = Math.round(entry.contentRect.height);
        setDims({ W, H, width: W, height: H });
      }
    });
    ob.observe(ref.current);
    return () => ob.disconnect();
  }, []);

  return [ref, dims];
}

