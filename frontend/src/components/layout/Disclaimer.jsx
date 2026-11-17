// The "not financial advice" notice (audit G-38). One text, used in the app shell, on the AAI card and in the
// landing footer, so the wording never drifts between places.
export const DISCLAIMER_TEXT =
  "AltInvest is for information and education only. It is not financial advice, and no score, signal, " +
  "range or estimate here is a recommendation to buy, sell or hold anything. Crypto assets and NFTs are " +
  "volatile and you can lose money. Do your own research.";

export const DISCLAIMER_SHORT = "Not financial advice: a rating, not a recommendation to buy or sell.";

export default function Disclaimer() {
  return (
    <p className="app-disclaimer sv2-small sv2-muted" role="note">
      {DISCLAIMER_TEXT}
    </p>
  );
}
