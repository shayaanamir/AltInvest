import { delayedTitle } from "../../utils/priceFreshness";

/** "Delayed" when a price (or NFT floor) is older than its limit (audit N-05); nothing otherwise. */
export default function DelayedBadge({ delayed, asOf, floor = false }) {
  if (!delayed) return null;
  return <span className="price-delayed-badge" title={delayedTitle(asOf, new Date(), { floor })}>Delayed</span>;
}
