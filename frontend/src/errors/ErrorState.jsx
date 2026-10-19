import { describeError } from "./errorCatalog";
import "./errors.css";

/**
 * Inline "this data failed to load" state.
 *   variant="panel"  — fills a card / page area (centered)
 *   variant="inline" — one row inside a list or small card
 * Pass `onRetry` (usually useAsync's `refetch`) to get a Retry button.
 */
export default function ErrorState({ error, onRetry, variant = "inline", title, message }) {
  const info = describeError(error);
  const headline = title || info.title;
  const body = message || info.message;

  return (
    <div className={`err-state ${variant}`} role="alert">
      <div className="err-state-icon" aria-hidden="true">!</div>
      <div>
        <div className="err-state-title">{headline}</div>
        <div className="err-state-msg">{body}</div>
        {variant === "panel" && info.raw && (
          <details className="err-state-details">
            <summary>Details</summary>
            {info.raw}
          </details>
        )}
      </div>
      {onRetry && info.retryable && (
        <div className="err-state-actions">
          <button type="button" className="err-btn" onClick={() => onRetry()}>Retry</button>
        </div>
      )}
    </div>
  );
}
