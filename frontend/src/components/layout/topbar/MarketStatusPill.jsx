import { motion } from "framer-motion";

// Crypto markets trade continuously — there's no exchange open/close
// schedule in the sample data to read this from, so "open" is a fixed
// platform fact rather than a fetched value.
export default function MarketStatusPill() {
  return (
    <div className="tb-status-pill">
      <motion.span
        className="tb-status-dot"
        animate={{ opacity: [1, 0.35, 1] }}
        transition={{ repeat: Infinity, duration: 2.4, ease: "easeInOut" }}
      />
      Markets open
    </div>
  );
}