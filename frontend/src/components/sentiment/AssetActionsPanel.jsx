import { useNavigate } from "react-router-dom";
import { IconBell, IconStar, IconFolder } from "../icons";

/**
 * Quick actions for the asset being viewed. `status` is the covered-universe row for it
 * ({ held, watching, ... }), `null` when the asset isn't covered (no portfolio, watchlist or alert
 * actions apply), or `undefined` while it loads. The parent owns the dialogs these buttons open.
 */
export default function AssetActionsPanel({ symbol, status, onAlert, onWatch, onHold }) {
  const navigate = useNavigate();
  const covered = !!status;
  const held = !!status?.held;
  const watching = !!status?.watching;
  const why = status === undefined ? "Loading…" : "Not in the covered universe";

  const links = [
    { label: "Open asset detail", disabled: !covered, onClick: () => navigate(`/asset-detail?symbol=${symbol}`) },
    { label: "Compare with something else", disabled: !covered, onClick: () => navigate(`/compare?ids=${symbol}`) },
    { label: "See your position", disabled: !held, hint: covered ? "You don't hold this" : why, onClick: () => navigate("/portfolio") },
    { label: "Browse more like this", disabled: false, onClick: () => navigate("/discover") },
  ];

  return (
    <div className="sv2-card sv2-card-pad-sm">
      <div className="sv2-card-title" style={{ marginBottom: 14 }}>Do something with this</div>

      <button className="sv2-btn-primary" onClick={onAlert} disabled={!covered} title={covered ? undefined : why}>
        <IconBell size={14} /> Alert me on changes
      </button>

      <div className="sv2-flex sv2-gap-10 sv2-mt-12">
        <button
          className={`sv2-btn-outline ${watching ? "active" : ""}`}
          onClick={onWatch}
          disabled={!covered}
          title={covered ? "Choose which watchlists include this" : why}
        >
          <IconStar size={13} filled={watching} /> Watching
        </button>
        <button
          className={`sv2-btn-outline ${held ? "active" : ""}`}
          onClick={held ? () => navigate("/portfolio") : onHold}
          disabled={!covered}
          title={covered ? (held ? "You hold this — open your portfolio" : "Add this to your portfolio") : why}
        >
          <IconFolder size={13} /> {held ? "In portfolio" : "Add to portfolio"}
        </button>
      </div>

      <div className="sv2-link-list sv2-mt-12">
        {links.map((l) => (
          <button key={l.label} onClick={l.onClick} disabled={l.disabled} title={l.disabled ? l.hint || why : undefined}>
            {l.label}<span>›</span>
          </button>
        ))}
      </div>
    </div>
  );
}
