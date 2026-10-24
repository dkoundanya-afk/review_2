/**
 * frontend/src/components/ErrorBoundary.jsx
 * Friendly generic error boundary screen (Task U4).
 */
import { Component } from "react";
import i18n from "../i18n.js";

export default class ErrorBoundary extends Component {
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

  handleReload = () => {
    window.location.reload();
  };

  handleHome = () => {
    window.location.href = "/";
  };

  render() {
    if (this.state.hasError) {
      const t = i18n.t.bind(i18n);
      return (
        <div className="min-vh-100 d-flex align-items-center justify-content-center p-3 bg-light">
          <div className="card border-0 shadow-sm p-4 text-center w-100" style={{ maxWidth: 420 }}>
            <div className="fs-1 mb-2" aria-hidden="true">⚠️</div>
            <h1 className="h5 fw-bold text-dark mb-2">
              {t("errors.generic_error")}
            </h1>
            <p className="text-muted small mb-4">
              {this.state.error?.message || t("errors.network_error")}
            </p>
            <div className="d-flex flex-column gap-2">
              <button
                type="button"
                className="btn btn-primary min-touch-target fw-semibold"
                onClick={this.handleReload}
              >
                {t("common.reload", { defaultValue: "Reload page" })}
              </button>
              <button
                type="button"
                className="btn btn-outline-secondary min-touch-target"
                onClick={this.handleHome}
              >
                {t("common.back_home", { defaultValue: "Back to Home" })}
              </button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
