import { useState } from "react";
import { createPortal } from "react-dom";
import { IconStar } from "../icons";
import WatchlistPickerModal from "./WatchlistPickerModal";

/**
 * A star that manages which of the user's watchlists an asset is on.
 *   item:     { type: "crypto" | "nft", id: symbol-or-slug, name }
 *   watching: whether it is on any watchlist right now (the parent reads this from the API and
 *             reloads when the watchlists change, so the star never keeps its own copy)
 * Clicking opens the watchlist picker; children, if given, are the button's label.
 */
export default function WatchStar({ item, watching, className = "sv2-star-btn", size = 16, title, children }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        className={`${className} ${watching ? "active" : ""}`}
        title={title || (watching ? "On your watchlists — manage" : "Add to a watchlist")}
        aria-label={`${watching ? "Manage watchlists for" : "Add to a watchlist:"} ${item.name}`}
        aria-pressed={!!watching}
        onClick={(e) => {
          e.stopPropagation(); // the star often sits inside a clickable card
          setOpen(true);
        }}
      >
        <IconStar size={size} filled={!!watching} />
        {children}
      </button>
      {open &&
        // Portalled to <body>, and shielded from bubbling: React events travel up the component tree,
        // so without this a click inside the dialog would also trigger the card the star sits in.
        createPortal(
          <div onClick={(e) => e.stopPropagation()}>
            <WatchlistPickerModal item={item} onClose={() => setOpen(false)} />
          </div>,
          document.body
        )}
    </>
  );
}
