import React from "react";
import { describeError } from "./errorCatalog";
import ErrorState from "./ErrorState";

/**
 * Catches a render crash so it blanks one area, not the whole app.
 *   <ErrorBoundary resetKey={pathname}>          — page level; clears itself when resetKey changes
 *   <ErrorBoundary variant="section" label="Portfolio intelligence"> — one card
 * "Try again" re-renders the children (no full reload); page level also offers "Go to dashboard".
 */
export default class ErrorBoundary extends React.Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("ErrorBoundary caught:", error, info?.componentStack);
  }

  componentDidUpdate(prev) {
    if (this.state.error && prev.resetKey !== this.props.resetKey) this.setState({ error: null });
  }

  reset = () => {
    this.setState({ error: null });
    this.props.onReset?.();
  };

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;
    if (this.props.fallback) return this.props.fallback;

    const section = this.props.variant === "section";
    const info = describeError(error, { kind: "render" });
    const title = section && this.props.label ? `${this.props.label} couldn't be shown` : info.title;

    return (
      <div className="sv2-card sv2-card-pad" style={section ? undefined : { maxWidth: 520, margin: "40px auto" }}>
        <ErrorState
          error={error}
          variant={section ? "inline" : "panel"}
          title={title}
          message="Part of this page failed to display."
        />
        <div className="err-state-actions" style={{ justifyContent: section ? "flex-start" : "center" }}>
          <button type="button" className="err-btn primary" onClick={this.reset}>Try again</button>
          {!section && (
            <button type="button" className="err-btn" onClick={() => { window.location.href = "/dashboard"; }}>
              Go to dashboard
            </button>
          )}
        </div>
      </div>
    );
  }
}
