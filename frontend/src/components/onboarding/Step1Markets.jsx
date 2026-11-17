import { useEffect, useState } from "react";
import { IconWallet, IconGrid2 } from "../icons";
import { discoverApi, defaultFilters } from "../../services/discoverApi";
import { togglePick } from "../../utils/onboardingPayload";
import OptionCard from "./OptionCard";
import StepHead from "./StepHead";

// Only the markets AltInvest actually covers. `category` is Discover's own name for it.
const MARKETS = [
  {
    key: "crypto", category: "crypto", title: "Crypto", unit: "coins",
    desc: "Coins and tokens, each with an AAI score, sentiment and risk reading.",
    icon: <IconWallet size={20} />,
  },
  {
    key: "nfts", category: "nft", title: "NFTs", unit: "collections",
    desc: "Collections with floor prices, sentiment and risk readings.",
    icon: <IconGrid2 size={20} />,
  },
];

/** How many assets AltInvest covers in each market, from the live universe. null until known or if it can't be read. */
function useCoverage() {
  const [counts, setCounts] = useState({ crypto: null, nft: null });
  useEffect(() => {
    let cancelled = false;
    MARKETS.forEach(({ category }) => {
      discoverApi
        .getPage(category, defaultFilters(), { limit: 1 })
        .then(({ total }) => !cancelled && setCounts((c) => ({ ...c, [category]: total })))
        .catch(() => {}); // the count is a nicety; the choice works without it
    });
    return () => { cancelled = true; };
  }, []);
  return counts;
}

export default function Step1Markets({ answers, setAnswer }) {
  const chosen = answers.markets || [];
  const counts = useCoverage();

  return (
    <>
      <StepHead
        eyebrow="Markets"
        title="Which markets do you follow?"
        sub="Pick one or both. This decides what we offer you to follow in a moment."
      />
      <div className="ob-grid cols-2" role="group" aria-label="Markets">
        {MARKETS.map((m) => {
          const n = counts[m.category];
          return (
            <OptionCard
              key={m.key}
              selected={chosen.includes(m.key)}
              onClick={() => setAnswer("markets", togglePick(chosen, m.key, MARKETS.length))}
              icon={m.icon}
              title={m.title}
              desc={m.desc}
              meta={n ? `${n.toLocaleString()} ${m.unit} covered` : undefined}
            />
          );
        })}
      </div>
      <p className="ob-note">Not sure yet? Skip this and you'll see both.</p>
    </>
  );
}
