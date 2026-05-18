import { useRef } from "react";
import { useInView } from "framer-motion";

export const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 28 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.65, ease: [0.22, 1, 0.36, 1], delay },
});

export const fadeIn = (delay = 0) => ({
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  transition: { duration: 0.55, delay },
});

export function useScrollReveal(threshold = 0.15) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-60px", amount: threshold });
  return { ref, inView };
}