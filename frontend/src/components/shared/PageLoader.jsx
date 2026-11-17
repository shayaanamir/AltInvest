/**
 * A centred spinner for a whole page or panel that is still loading (a lazy page chunk, or settings the
 * page needs before it can lay itself out). Small inline loads keep using `.sv2-spinner` directly.
 * The label is for screen readers and shows under the spinner.
 */
export default function PageLoader({ label = "Loading" }) {
  return (
    <div className="sv2-pageloader" role="status" aria-live="polite">
      <span className="sv2-spinner sv2-spinner-lg" aria-hidden="true" />
      <span className="sv2-pageloader-label">{label}</span>
    </div>
  );
}
