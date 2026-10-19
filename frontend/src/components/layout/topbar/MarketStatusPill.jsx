import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { isApiReachable, subscribeConnection } from "../../../errors/connectionStatus";

// Reflects whether the app can currently reach the data service, not a claim about any exchange.
export default function MarketStatusPill() {
  const [live, setLive] = useState(isApiReachable);

  useEffect(() => subscribeConnection(() => setLive(isApiReachable())), []);

  return (
    <div className="tb-status-pill" style={live ? undefined : { color: "var(--sv2-red)" }}>
      <motion.span
        className="tb-status-dot"
        style={live ? undefined : { background: "var(--sv2-red)" }}
        animate={{ opacity: live ? [1, 0.35, 1] : 1 }}
        transition={{ repeat: live ? Infinity : 0, duration: 2.4, ease: "easeInOut" }}
      />
      {live ? "Live data" : "Offline"}
    </div>
  );
}
