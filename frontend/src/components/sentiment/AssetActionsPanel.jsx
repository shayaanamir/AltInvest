import { useState } from "react";
import { IconBell, IconStar, IconFolder } from "./icons";

const LINKS = ["Open asset detail", "Compare with something else", "See your position", "Browse more like this"];

export default function AssetActionsPanel({ watching, onToggleWatching, held }) {
  const [confirmed, setConfirmed] = useState(false);
  const [inPortfolio, setInPortfolio] = useState(held);

  const handleAlert = () => {
    setConfirmed(true);
    setTimeout(() => setConfirmed(false), 2500);
  };

  return (
    <div className="sv2-card sv2-card-pad-sm">
      <div className="sv2-card-title" style={{ marginBottom: 14 }}>Do something with this</div>

      <button className="sv2-btn-primary" onClick={handleAlert}>
        <IconBell size={14} /> {confirmed ? "You're set — we'll let you know" : "Alert me on changes"}
      </button>

      <div className="sv2-flex sv2-gap-10 sv2-mt-12">
        <button className={`sv2-btn-outline ${watching ? "active" : ""}`} onClick={onToggleWatching}>
          <IconStar size={13} filled={watching} /> Watching
        </button>
        <button className={`sv2-btn-outline ${inPortfolio ? "active" : ""}`} onClick={() => setInPortfolio((v) => !v)}>
          <IconFolder size={13} /> In portfolio
        </button>
      </div>

      <div className="sv2-link-list sv2-mt-12">
        {LINKS.map((l) => (
          <button key={l}>{l}<span>›</span></button>
        ))}
      </div>
    </div>
  );
}