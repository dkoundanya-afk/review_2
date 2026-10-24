/**
 * frontend/src/screens/BadgesScreen.jsx
 * Badges screen (Task U4).
 * Fetches GET /progress and shows all badges:
 *   - Earned: full colour, emoji icon, earned date.
 *   - Locked: greyed out, description only.
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import api, { getTranslatedError } from "../api.js";

function SkeletonBadge() {
  return (
    <div className="card border-0 shadow-sm p-3 mb-1 skeleton-card" aria-hidden="true">
      <div className="d-flex align-items-center gap-3">
        <div className="skeleton-box rounded-circle" style={{ width: 48, height: 48 }} />
        <div className="flex-grow-1">
          <div className="skeleton-box mb-2" style={{ height: 14, width: "55%" }} />
          <div className="skeleton-box" style={{ height: 12, width: "80%" }} />
        </div>
      </div>
    </div>
  );
}

export default function BadgesScreen() {
  const { t, i18n } = useTranslation();
  const [badges, setBadges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    document.title = `${t("badges.title")} — ${t("app_name")}`;
  }, [t, i18n.language]);

  useEffect(() => {
    let isMounted = true;
    async function loadBadges() {
      setLoading(true);
      setError(null);
      try {
        const data = await api.get("/progress");
        if (isMounted && data.badges) {
          setBadges(data.badges);
        }
      } catch (err) {
        if (isMounted) setError(getTranslatedError(t, err));
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    loadBadges();
    return () => { isMounted = false; };
  }, [t]);

  const earned = badges.filter((b) => b.earned);
  const locked = badges.filter((b) => !b.earned);

  return (
    <div className="badges-screen pb-5">
      <h1 className="h4 fw-bold mb-1">{t("badges.title")}</h1>
      <p className="text-muted small mb-4">
        {t("badges.subtitle", { earned: earned.length, total: badges.length })}
      </p>

      {/* Error state */}
      {error && (
        <div className="alert alert-danger shadow-sm py-2 px-3 small mb-3" role="alert">
          ⚠️ {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="d-flex flex-column gap-2" aria-label={t("common.loading")}>
          {[1, 2, 3, 4].map((n) => <SkeletonBadge key={n} />)}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && badges.length === 0 && (
        <div className="card border-0 shadow-sm p-5 text-center">
          <div className="fs-1 mb-2" aria-hidden="true">🏅</div>
          <p className="text-muted mb-0">{t("badges.empty")}</p>
        </div>
      )}

      {/* Earned badges */}
      {!loading && earned.length > 0 && (
        <div className="mb-4">
          <h2 className="h6 fw-bold text-success mb-2">
            🏆 {t("badges.earned_section")} ({earned.length})
          </h2>
          <div className="d-flex flex-column gap-2">
            {earned.map((b) => (
              <div
                key={b.key}
                className="card border-0 shadow-sm p-3 bg-white"
              >
                <div className="d-flex align-items-start gap-3">
                  <div
                    className="badge-icon-lg flex-shrink-0 d-flex align-items-center justify-content-center rounded-circle bg-success-subtle border border-success-subtle"
                    style={{ width: 48, height: 48 }}
                    aria-hidden="true"
                  >
                    <span className="fs-4">🎖️</span>
                  </div>
                  <div className="flex-grow-1 min-w-0">
                    <div className="d-flex justify-content-between align-items-start">
                      <h3 className="h6 fw-bold mb-0 text-dark">{b.name}</h3>
                      <span className="badge bg-success ms-2 flex-shrink-0">
                        {t("badges.earned_label")}
                      </span>
                    </div>
                    <p className="small text-muted mb-1">{b.description}</p>
                    {b.earned_at && (
                      <p className="extra-small text-muted mb-0">
                        🗓️ {t("badges.earned_on", {
                          date: new Date(b.earned_at).toLocaleDateString(
                            i18n.language === "kn" ? "kn-IN" : "en-IN",
                            { year: "numeric", month: "short", day: "numeric" }
                          ),
                        })}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Locked badges */}
      {!loading && locked.length > 0 && (
        <div>
          <h2 className="h6 fw-bold text-muted mb-2">
            🔒 {t("badges.locked_section")} ({locked.length})
          </h2>
          <div className="d-flex flex-column gap-2">
            {locked.map((b) => (
              <div
                key={b.key}
                className="card border-0 shadow-sm p-3"
                style={{ opacity: 0.65, backgroundColor: "#f8f9fa" }}
              >
                <div className="d-flex align-items-start gap-3">
                  <div
                    className="flex-shrink-0 d-flex align-items-center justify-content-center rounded-circle bg-light border"
                    style={{ width: 48, height: 48 }}
                    aria-hidden="true"
                  >
                    <span className="fs-4 grayscale">🎖️</span>
                  </div>
                  <div className="flex-grow-1 min-w-0">
                    <div className="d-flex justify-content-between align-items-start">
                      <h3 className="h6 fw-semibold mb-0 text-muted">{b.name}</h3>
                      <span className="badge bg-secondary ms-2 flex-shrink-0">
                        {t("badges.locked_label")}
                      </span>
                    </div>
                    <p className="small text-muted mb-0">{b.description}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
