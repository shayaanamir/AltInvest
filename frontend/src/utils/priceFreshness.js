// How old a price is (audit N-05). The backend sends price_as_of (ISO UTC) and price_delayed: true when a crypto
// price is more than 15 minutes old (the market snapshot stalled), or an NFT floor more than 48 hours old (floors are
// daily). Pure helpers so node --test can check them.

const pad = (n) => String(n).padStart(2, "0");

/** "as of 14:32 UTC" today, "as of 16 Nov, 14:32 UTC" on another day; null without a usable time. */
export function priceAsOfLabel(iso, now = new Date()) {
  if (!iso) return null;
  const t = new Date(iso);
  if (Number.isNaN(t.getTime())) return null;
  const hm = `${pad(t.getUTCHours())}:${pad(t.getUTCMinutes())} UTC`;
  const sameDay = t.getUTCFullYear() === now.getUTCFullYear() && t.getUTCMonth() === now.getUTCMonth()
    && t.getUTCDate() === now.getUTCDate();
  if (sameDay) return `as of ${hm}`;
  const month = t.toLocaleString("en-GB", { month: "short", timeZone: "UTC" });
  return `as of ${t.getUTCDate()} ${month}, ${hm}`;
}

/** Tooltip for a delayed price, or (floor: true) a delayed NFT floor. */
export function delayedTitle(iso, now = new Date(), { floor = false } = {}) {
  const label = priceAsOfLabel(iso, now);
  const what = floor ? "This floor price has not updated for over 48 hours" : "This price has not updated for over 15 minutes";
  return `${what}${label ? ` (${label})` : ""}.`;
}
