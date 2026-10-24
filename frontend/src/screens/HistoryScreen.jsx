/**
 * frontend/src/screens/HistoryScreen.jsx
 * History screen (Task U4).
 * GET /history -> attempts list (tap to open /result/<id>) + points ledger.
 * Points reasons are translated via points.* keys from en.json.
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import api, { getTranslatedError } from "../api.js";
import { FormattedFormula } from "../components/IonDisplay.jsx";

function SkeletonRow() {
  return (
    <div className="card border-0 shadow-sm p-3 mb-1 skeleton-card" aria-hidden="true">
      <div className="d-flex justify-content-between align-items-center">
        <div className="flex-grow-1">
          <div className="skeleton-box mb-2" style={{ height: 14, width: "60%" }} />
          <div className="skeleton-box" style={{ height: 12, width: "40%" }} />
        </div>
        <div className="skeleton-box rounded" style={{ width: 60, height: 28 }} />
      </div>
    </div>
  );
}

export default function HistoryScreen() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("attempts");

  useEffect(() => {
    document.title = `${t("history.title")} — ${t("app_name")}`;
  }, [t, i18n.language]);

  useEffect(() => {
    let isMounted = true;
    async function loadHistory() {
      setLoading(true);
      setError(null);
      try {
        const data = await api.get("/history");
        if (isMounted) setHistory(data);
      } catch (err) {
        if (isMounted) setError(getTranslatedError(t, err));
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    loadHistory();
    return () => { isMounted = false; };
  }, [t]);

  const formatDate = (iso) => {
    if (!iso) return "";
    try {
      return new Date(iso).toLocaleDateString(
        i18n.language === "kn" ? "kn-IN" : "en-IN",
        { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }
      );
    } catch {
      return iso;
    }
  };

  const attempts = history?.attempts || [];
  const ledger = history?.ledger || [];

  const hasAttempts = attempts.length > 0;
  const hasLedger = ledger.length > 0;
  const isEmpty = !hasAttempts && !hasLedger;

  return (
    <div className="history-screen pb-5">
      <h1 className="h4 fw-bold mb-1">{t("history.title")}</h1>
      <p className="text-muted small mb-3">{t("history.subtitle")}</p>

      {/* Error state */}
      {error && (
        <div className="alert alert-danger shadow-sm py-2 px-3 small mb-3" role="alert">
          ⚠️ {error}
        </div>
      )}

      {/* Loading skeletons */}
      {loading && (
        <div aria-label={t("common.loading")}>
          {[1, 2, 3].map((n) => <SkeletonRow key={n} />)}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && isEmpty && (
        <div className="card border-0 shadow-sm p-5 text-center">
          <div className="fs-1 mb-2" aria-hidden="true">📋</div>
          <p className="fw-semibold text-dark mb-1">{t("history.empty_title")}</p>
          <p className="text-muted small mb-0">{t("history.empty_hint")}</p>
        </div>
      )}

      {/* Tabs */}
      {!loading && !error && !isEmpty && (
        <>
          <div className="nav nav-tabs mb-3" role="tablist">
            <button
              role="tab"
              aria-selected={activeTab === "attempts"}
              className={`nav-link ${activeTab === "attempts" ? "active fw-bold" : ""}`}
              onClick={() => setActiveTab("attempts")}
            >
              {t("history.tab_attempts")}
              {hasAttempts && (
                <span className="badge bg-secondary ms-1">{attempts.length}</span>
              )}
            </button>
            <button
              role="tab"
              aria-selected={activeTab === "ledger"}
              className={`nav-link ${activeTab === "ledger" ? "active fw-bold" : ""}`}
              onClick={() => setActiveTab("ledger")}
            >
              {t("history.tab_ledger")}
              {hasLedger && (
                <span className="badge bg-secondary ms-1">{ledger.length}</span>
              )}
            </button>
          </div>

          {/* Attempts tab */}
          {activeTab === "attempts" && (
            <div role="tabpanel">
              {!hasAttempts ? (
                <div className="text-muted small text-center py-4">{t("history.no_attempts")}</div>
              ) : (
                <div className="d-flex flex-column gap-2">
                  {attempts.map((a) => {
                    const scoreColor =
                      a.percent >= 75 ? "bg-success" :
                      a.percent >= 50 ? "bg-warning text-dark" : "bg-danger";
                    return (
                      <button
                        key={a.attempt_id}
                        type="button"
                        className="card border-0 shadow-sm p-3 text-start w-100 attempt-row"
                        onClick={() => navigate(`/result/${a.attempt_id}`)}
                        aria-label={t("history.open_result_aria", { name: a.name })}
                      >
                        <div className="d-flex justify-content-between align-items-start">
                          <div className="flex-grow-1 me-2 min-w-0">
                            <div className="fw-bold text-dark d-flex align-items-center gap-1 mb-1">
                              <FormattedFormula formula={a.formula} />
                              <span className="fw-normal text-muted small ms-1">({a.name})</span>
                            </div>
                            <div className="d-flex gap-2 align-items-center flex-wrap">
                              {a.is_practice && (
                                <span className="badge bg-secondary-subtle text-secondary border border-secondary-subtle extra-small">
                                  {t("result.practice_mode")}
                                </span>
                              )}
                              <span className="extra-small text-muted">
                                {formatDate(a.submitted_at)}
                              </span>
                            </div>
                          </div>
                          <div className="text-end flex-shrink-0">
                            <span className={`badge ${scoreColor} fs-6 px-2`}>
                              {a.correct}/{a.total}
                            </span>
                            <div className="extra-small text-muted mt-1">{a.percent}%</div>
                          </div>
                        </div>
                        <div className="text-primary extra-small mt-1">{t("history.tap_for_result")} →</div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Ledger tab */}
          {activeTab === "ledger" && (
            <div role="tabpanel">
              {!hasLedger ? (
                <div className="text-muted small text-center py-4">{t("history.no_ledger")}</div>
              ) : (
                <>
                  <div className="d-flex justify-content-between align-items-center mb-2 px-1">
                    <span className="small text-muted">{t("history.total_points")}</span>
                    <span className="fw-bold text-primary">
                      +{ledger.reduce((sum, l) => sum + (l.delta > 0 ? l.delta : 0), 0)} pts
                    </span>
                  </div>
                  <div className="d-flex flex-column gap-2">
                    {ledger.map((l, idx) => (
                      <div
                        key={idx}
                        className="card border-0 shadow-sm p-3 bg-white d-flex flex-row justify-content-between align-items-center"
                      >
                        <div className="small text-dark">
                          {t(`points.${l.reason}`, l.reason)}
                          {l.created && (
                            <div className="extra-small text-muted mt-1">{formatDate(l.created)}</div>
                          )}
                        </div>
                        <span
                          className={`badge font-monospace fs-6 ${
                            l.delta >= 0 ? "bg-success-subtle text-success border border-success-subtle" : "bg-danger-subtle text-danger border border-danger-subtle"
                          }`}
                        >
                          {l.delta >= 0 ? "+" : ""}{l.delta}
                        </span>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
