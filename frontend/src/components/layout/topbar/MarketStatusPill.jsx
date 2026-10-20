import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { getApiState, subscribeConnection } from "../../../errors/connectionStatus";

// Reflects whether the app can currently reach the data service, not a claim about any exchange.
// "Live data" is only shown once a request has actually succeeded; before that it says so.
const LABELS = { up: "Live data", down: "Offline", unknown: "Connecting…" };

export default function MarketStatusPill() {
  const [state, setState] = useState(getApiState);

  useEffect(() => subscribeConnection(() => setState(getApiState())), []);

  const live = state === "up";
  const down = state === "down";

  return (
    <div className="tb-status-pill" style={down ? { color: "var(--sv2-red)" } : undefined}>
      <motion.span
        className="tb-status-dot"
        style={down ? { background: "var(--sv2-red)" } : undefined}
        animate={{ opacity: live ? [1, 0.35, 1] : 1 }}
        transition={{ repeat: live ? Infinity : 0, duration: 2.4, ease: "easeInOut" }}
      />
      {LABELS[state]}
    </div>
  );
}
