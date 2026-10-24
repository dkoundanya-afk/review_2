/**
 * frontend/src/screens/HomeScreen.jsx
 * Student home dashboard for Task U2.
 * Shows:
 *  - Welcome & student details
 *  - Big "Redeem a code" CTA button
 *  - Points and level progress bar (progress to next level using level.next)
 *  - Horizontal scrollable strip of earned badges
 *  - 2-column responsive grid (at 360px) of 12 salts with blue/orange chips
 *  - Live freshness: refetches on focus, visibility change, and custom refresh event
 */
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useSession } from "../session.jsx";
import api from "../api.js";
import SaltCard from "../components/SaltCard.jsx";

export default function HomeScreen() {
  const { t, i18n } = useTranslation();
  const { me } = useSession();
  const navigate = useNavigate();

  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);
  const [quizNotice, setQuizNotice] = useState(null);
  const [startingQuizId, setStartingQuizId] = useState(null);

  useEffect(() => {
    document.title = t("app_name") + " — " + t("app_tagline");
  }, [t, i18n.language]);

  // Fetch progress data from GET /progress and keep fresh on focus / visibility / redeem
  useEffect(() => {
    let isMounted = true;

    async function loadProgress() {
      try {
        const data = await api.get("/progress");
        if (isMounted) {
          setProgress(data);
          setLoading(false);
        }
      } catch (err) {
        console.error("Failed to load progress:", err);
        if (isMounted) setLoading(false);
      }
    }

    loadProgress();

    const handleFocus = () => loadProgress();
    const handleVisibility = () => {
      if (document.visibilityState === "visible") loadProgress();
    };
    const handleRefresh = () => loadProgress();

    window.addEventListener("focus", handleFocus);
    document.addEventListener("visibilitychange", handleVisibility);
    window.addEventListener("vl:refresh_progress", handleRefresh);

    return () => {
      isMounted = false;
      window.removeEventListener("focus", handleFocus);
      document.removeEventListener("visibilitychange", handleVisibility);
      window.removeEventListener("vl:refresh_progress", handleRefresh);
    };
  }, []);

  // Handle quiz start/practice
  const handleStartQuiz = async (redemptionId, isPractice = false) => {
    setStartingQuizId(redemptionId);
    setQuizNotice(null);
    try {
      const res = await api.post("/quiz/start", {
        redemption_id: redemptionId,
        practice: isPractice,
      });
      if (res?.attempt_id) {
        localStorage.setItem(`vl_quiz_redemption_${res.attempt_id}`, String(redemptionId));
        navigate(`/quiz/${res.attempt_id}`);
      }
    } catch {
      // Quiz backend is added later: show friendly message on 404
      setQuizNotice(t("quiz.not_available_yet"));
    } finally {
      setStartingQuizId(null);
    }
  };

  const handleResumeQuiz = (attemptId) => {
    navigate(`/quiz/${attemptId}`);
  };

  const handleOpenResult = (attemptId) => {
    navigate(`/result/${attemptId}`);
  };

  // Level progress calculations
  const points = progress?.points ?? 0;
  const currentLevel = progress?.level;
  const nextLevel = currentLevel?.next;

  let levelProgressPercent = 100;
  let pointsToNext = 0;
  if (nextLevel) {
    const minPts = currentLevel?.min_points ?? 0;
    const maxPts = nextLevel.min_points ?? 100;
    const range = Math.max(1, maxPts - minPts);
    const earned = Math.max(0, points - minPts);
    levelProgressPercent = Math.min(100, Math.max(0, Math.round((earned / range) * 100)));
    pointsToNext = Math.max(0, maxPts - points);
  }

  const earnedBadges = (progress?.badges || []).filter((b) => b.earned);
  const items = progress?.items || [];
  const className = me?.classes && me.classes.length > 0 ? me.classes[0].name : null;

  return (
    <div className="home-screen pb-5">
      {/* Friendly Quiz Availability Notice */}
      {quizNotice && (
        <div
          className="alert alert-info alert-dismissible fade show shadow-sm mb-3 d-flex align-items-center justify-content-between"
          role="alert"
        >
          <div className="d-flex align-items-center gap-2">
            <span>ℹ️</span>
            <span>{quizNotice}</span>
          </div>
          <button
            type="button"
            className="btn-close ms-2"
            aria-label="Close"
            onClick={() => setQuizNotice(null)}
          />
        </div>
      )}

      {/* Welcome Banner */}
      <div className="card border-0 shadow-sm mb-3 bg-primary text-white overflow-hidden">
        <div className="card-body p-3 p-sm-4">
          <div className="d-flex justify-content-between align-items-center">
            <div>
              <h1 className="h5 fw-bold mb-1">
                {t("home.welcome", { name: me?.display_name || me?.id || "Student" })}
              </h1>
              <div className="d-flex flex-wrap gap-2 text-white-50 small mt-1">
                <span className="badge bg-white text-primary fw-medium px-2 py-1">
                  {t("home.student_id", { id: me?.id })}
                </span>
                <span className="badge bg-light bg-opacity-25 text-white fw-medium px-2 py-1">
                  {className ? t("home.enrolled_class", { name: className }) : t("home.not_enrolled")}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Big "Redeem a code" CTA Button (Requirement 2) */}
      <Link
        to="/redeem"
        className="btn btn-warning btn-lg w-100 min-touch-target fw-bold shadow-sm d-flex align-items-center justify-content-center gap-2 mb-3 text-dark text-decoration-none"
      >
        <span className="fs-5" aria-hidden="true">🔑</span>
        <span>{t("home.redeem_action")}</span>
      </Link>

      {/* Points & Level Bar (Requirement 1) */}
      <div className="card border-0 shadow-sm mb-3 bg-white">
        <div className="card-body p-3">
          <div className="d-flex justify-content-between align-items-baseline mb-1">
            <div>
              <span className="text-muted small fw-medium text-uppercase">
                {t("home.level")}:{" "}
              </span>
              <span className="fw-bold text-dark fs-5">
                {currentLevel?.name || "Beginner"}
              </span>
            </div>
            <div className="text-end">
              <span className="fs-4 fw-bold text-primary">{points}</span>
              <span className="text-muted small"> pts</span>
            </div>
          </div>

          {/* Level Progress Bar */}
          <div className="progress mt-2 mb-2" style={{ height: "10px" }}>
            <div
              className="progress-bar bg-primary"
              role="progressbar"
              style={{ width: `${levelProgressPercent}%` }}
              aria-valuenow={levelProgressPercent}
              aria-valuemin="0"
              aria-valuemax="100"
            />
          </div>

          {/* Next Level or Max Level Info */}
          <div className="d-flex justify-content-between text-muted small">
            <span>{levelProgressPercent}%</span>
            <span>
              {nextLevel
                ? t("home.points_to_next", {
                    remaining: pointsToNext,
                    nextLevel: nextLevel.name,
                  })
                : t("home.max_level")}
            </span>
          </div>
        </div>
      </div>

      {/* Horizontal Strip of Earned Badges (Requirement 1) */}
      <div className="card border-0 shadow-sm mb-4 bg-white">
        <div className="card-body p-3">
          <div className="d-flex justify-content-between align-items-center mb-2">
            <h2 className="h6 fw-bold mb-0 text-dark">
              {t("home.earned_badges")} ({earnedBadges.length})
            </h2>
            <Link to="/badges" className="small text-decoration-none fw-semibold">
              {t("home.view_all_badges")} &rarr;
            </Link>
          </div>

          {earnedBadges.length === 0 ? (
            <div className="p-3 bg-light rounded text-center">
              <p className="small text-muted mb-0">{t("home.no_badges_yet")}</p>
            </div>
          ) : (
            <div className="badges-strip">
              {earnedBadges.map((badge) => (
                <div
                  key={badge.key}
                  className="badge-strip-item p-2 flex-shrink-0 text-center shadow-sm"
                  title={badge.description}
                >
                  <div className="badge-icon fs-3 mb-1" aria-hidden="true">🏅</div>
                  <div className="badge-name fw-bold small text-truncate" title={badge.name}>
                    {badge.name}
                  </div>
                  <div
                    className="badge-desc text-muted extra-small text-truncate"
                    title={badge.description}
                  >
                    {badge.description}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Grid of the 12 Salts (2 columns at 360 px) (Requirement 1) */}
      <div className="mb-4">
        <div className="d-flex justify-content-between align-items-center mb-2 px-1">
          <h2 className="h6 fw-bold mb-0 text-dark">{t("home.salts_title")}</h2>
          <span className="small text-muted">
            {t("home.completed_count", {
              completed: progress?.completed ?? 0,
              total: progress?.total_items ?? 12,
            })}
          </span>
        </div>

        {loading ? (
          <div className="salt-grid" aria-hidden="true">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="card salt-card p-3 skeleton-card">
                <div className="skeleton-box mb-2" style={{ height: 22, width: "50%" }} />
                <div className="skeleton-box mb-2" style={{ height: 14, width: "80%" }} />
                <div className="skeleton-box mb-3" style={{ height: 18, width: "100%" }} />
                <div className="skeleton-box mt-auto" style={{ height: 32, width: "100%", borderRadius: 6 }} />
              </div>
            ))}
          </div>
        ) : (
          <div className="salt-grid">
            {items.map((item) => (
              <SaltCard
                key={item.item}
                item={item}
                onStartQuiz={handleStartQuiz}
                onOpenResult={handleOpenResult}
                onResumeQuiz={handleResumeQuiz}
                isStarting={startingQuizId === item.redemption_id}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
