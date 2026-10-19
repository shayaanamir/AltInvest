import React from "react";
import systemStates from "../../data/sample_data/systemStates.json";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    if (this.props.onReset) {
      this.props.onReset();
    } else {
      window.location.reload();
    }
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const copy = systemStates.errorBoundary || {
        title: "Something went wrong",
        subtitle: "An unexpected error occurred while loading this page.",
        cta: "Reload",
      };

      return (
        <div
          className="sv2-card sv2-card-pad"
          style={{
            maxWidth: 500,
            margin: "40px auto",
            textAlign: "center",
            padding: "36px 24px",
          }}
        >
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: "50%",
              background: "var(--sv2-red-soft, rgba(255, 77, 77, 0.12))",
              color: "var(--sv2-red, #ff4d4d)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 20,
              fontWeight: 800,
              margin: "0 auto 16px",
            }}
          >
            !
          </div>
          <h2 className="sv2-card-title" style={{ fontSize: 18, marginBottom: 8 }}>
            {copy.title}
          </h2>
          <p className="sv2-card-sub" style={{ marginBottom: 20 }}>
            {copy.subtitle}
          </p>
          <button
            type="button"
            className="sv2-btn-primary"
            onClick={this.handleReset}
            style={{
              padding: "8px 24px",
              borderRadius: 8,
              cursor: "pointer",
            }}
          >
            {copy.cta}
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
