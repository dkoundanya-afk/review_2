/**
 * frontend/src/screens/ResultScreen.jsx
 * Quiz Results screen for Task U3.
 * Features:
 *  - Score and percent.
 *  - Points breakdown lines (and "No points for practice" for practice mode).
 *  - Level before/after with celebratory level-up banner when leveled_up.
 *  - Toasts / banners for new_badges.
 *  - List of every question with student's answer, correct answer, correct/incorrect marking and explanation.
 *  - Weak topics list (test_type with underscores as spaces, radical with sub/superscripts).
 *  - Insights and feedback lists translated by key (unknown key hidden; ion chips for wrong_guess).
 *  - Buttons "Back to home" and (for non-practice) "Practice again" calling POST /quiz/start {redemption_id, practice: true}.
 */
import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import api, { getTranslatedError } from "../api.js";
import { FormattedIon, IonChip } from "../components/IonDisplay.jsx";

export default function ResultScreen() {
  const { t, i18n } = useTranslation();
  const { id } = useParams();
  const navigate = useNavigate();

  useEffect(() => {
    document.title = `${t("result.title")} — ${t("app_name")}`;
  }, [t, i18n.language]);

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [result, setResult] = useState(null);

  const [startingPractice, setStartingPractice] = useState(false);
  const [practiceError, setPracticeError] = useState(null);

  useEffect(() => {
    let isMounted = true;

    async function loadResult() {
      setLoading(true);
      setLoadError(null);
      try {
        const data = await api.get(`/quiz/${id}/result`);
        if (isMounted) {
          setResult(data);
          setLoading(false);
          // Notify app to refresh progress points / badges in background
          window.dispatchEvent(new CustomEvent("vl:refresh_progress"));
        }
      } catch (err) {
        if (isMounted) {
          setLoadError(getTranslatedError(t, err));
          setLoading(false);
        }
      }
    }

    loadResult();

    return () => {
      isMounted = false;
    };
  }, [id, t]);

  // Handle Practice Again
  const handlePracticeAgain = async () => {
    setStartingPractice(true);
    setPracticeError(null);

    try {
      // Find redemption_id from localStorage or /progress
      let redemptionId = localStorage.getItem(`vl_quiz_redemption_${id}`);

      if (!redemptionId) {
        const prog = await api.get("/progress");
        const match = prog.items?.find((item) => String(item.attempt_id) === String(id));
        if (match?.redemption_id) {
          redemptionId = match.redemption_id;
        }
      }

      if (!redemptionId) {
        throw new Error("Could not find salt redemption ID for practice.");
      }

      const res = await api.post("/quiz/start", {
        redemption_id: Number(redemptionId),
        practice: true,
      });

      if (res?.attempt_id) {
        localStorage.setItem(`vl_quiz_redemption_${res.attempt_id}`, String(redemptionId));
        navigate(`/quiz/${res.attempt_id}`);
      }
    } catch (err) {
      setPracticeError(getTranslatedError(t, err) || "Failed to start practice session.");
    } finally {
      setStartingPractice(false);
    }
  };

  // Helper to translate insight / feedback key safely (hide unknown keys)
  const getTranslatedEntry = (key, params = {}) => {
    if (!key) return null;
    if (!i18n.exists(key) && t(key) === key) {
      return null; // Hide unknown key
    }
    return t(key, params);
  };

  if (loading) {
    return (
      <div className="text-center py-5">
        <div className="spinner-border text-primary mb-3" role="status" />
        <p className="text-muted small">{t("common.loading")}</p>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="result-error py-4">
        <div className="alert alert-danger shadow-sm mb-3">
          <strong>⚠️ {t("errors.generic_error")}</strong>
          <p className="mb-0 mt-1 small">{loadError}</p>
        </div>
        <Link to="/" className="btn btn-outline-secondary min-touch-target">
          &larr; {t("common.back")}
        </Link>
      </div>
    );
  }

  const {
    score = { correct: 0, total: 0, percent: 0 },
    is_practice = false,
    points = { total: 0, lines: [] },
    new_badges = [],
    level_before,
    level_after,
    leveled_up = false,
    review = [],
    weak_topics = [],
    insights = [],
    feedback = [],
    no_lab_data = false,
  } = result || {};

  return (
    <div className="result-screen pb-5">
      {/* Top Header */}
      <div className="d-flex align-items-center mb-3">
        <Link
          to="/"
          className="btn btn-sm btn-outline-secondary min-touch-target px-2 py-1 me-2"
          title={t("common.back")}
          aria-label={t("common.back")}
        >
          &larr;
        </Link>
        <h1 className="h4 fw-bold mb-0">{t("result.title")}</h1>
        {is_practice && (
          <span className="badge bg-secondary-subtle text-secondary border border-secondary-subtle ms-2">
            {t("result.practice_mode")}
          </span>
        )}
      </div>

      {/* Lab Data Not Available Notice */}
      {no_lab_data && (
        <div className="alert alert-info py-2 px-3 small mb-3 shadow-sm">
          ℹ️ {t("salt.no_lab_data")}
        </div>
      )}

      {/* Level Up Banner */}
      {leveled_up && level_after && (
        <div className="card border-0 shadow-sm bg-primary text-white p-3 mb-3 text-center">
          <div className="fs-1" aria-hidden="true">⭐</div>
          <h2 className="h4 fw-bold mb-1">{t("result.level_up")}</h2>
          <p className="mb-0 fw-medium">
            {t("result.level_up_congrats", { level: level_after.name })}
          </p>
        </div>
      )}

      {/* New Badges Banners / Toasts */}
      {new_badges && new_badges.length > 0 && (
        <div className="alert alert-success d-flex flex-column gap-2 mb-3 shadow-sm">
          <div className="fw-bold small text-success-emphasis">
            🎉 {t("result.new_badges_title")}
          </div>
          {new_badges.map((b) => (
            <div key={b.key} className="d-flex align-items-start gap-2 bg-white p-2 rounded border border-success-subtle">
              <span className="fs-4" aria-hidden="true">🎖️</span>
              <div>
                <strong className="d-block text-dark">{b.name}</strong>
                <small className="text-muted">{b.description}</small>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Score Summary Card */}
      <div className="card border-0 shadow-sm p-4 text-center mb-3 bg-white">
        <div className="text-muted small text-uppercase fw-semibold mb-1">
          {t("result.score_title")}
        </div>
        <div className="display-5 fw-bold text-dark mb-1">
          {score.correct} <span className="text-muted fs-4">/ {score.total}</span>
        </div>
        <div className="fs-4 fw-bold text-primary mb-2">
          {score.percent}%
        </div>

        {/* Level Progression Indicator */}
        {level_before && level_after && (
          <div className="small text-muted border-top pt-2 mt-2">
            <span className="fw-medium">
              {t("result.level_label", {
                before: level_before.name,
                after: level_after.name,
              })}
            </span>
          </div>
        )}
      </div>

      {/* Points Breakdown Section */}
      <div className="card border-0 shadow-sm p-3 p-sm-4 mb-3 bg-white">
        <div className="d-flex justify-content-between align-items-center mb-2">
          <h2 className="h6 fw-bold mb-0">{t("result.points_breakdown")}</h2>
          {!is_practice ? (
            <span className="badge bg-success-subtle text-success fs-6 border border-success-subtle px-2 py-1">
              +{points.total} pts
            </span>
          ) : (
            <span className="badge bg-light text-muted border">
              0 pts
            </span>
          )}
        </div>

        {is_practice ? (
          <p className="text-muted small mb-0 fst-italic">
            {t("result.practice_no_points")}
          </p>
        ) : points.lines && points.lines.length > 0 ? (
          <div className="list-group list-group-flush small">
            {points.lines.map((line, idx) => (
              <div
                key={idx}
                className="list-group-item d-flex justify-content-between align-items-center px-0 py-2"
              >
                <span className="text-dark">
                  {t(`points.${line.reason}`, line.reason)}
                </span>
                <span className="fw-bold text-success font-monospace">
                  +{line.delta}
                </span>
              </div>
            ))}
          </div>
        ) : (
        <p className="text-muted small mb-0">{t("result.no_points_earned")}</p>
        )}
      </div>

      {/* Weak Topics List */}
      {weak_topics && weak_topics.length > 0 && (
        <div className="card border-0 shadow-sm p-3 p-sm-4 mb-3 bg-white">
          <h2 className="h6 fw-bold text-danger mb-2">
            ⚠️ {t("result.weak_topics_title")}
          </h2>
          <div className="d-flex flex-column gap-2">
            {weak_topics.map((topic, idx) => (
              <div
                key={idx}
                className="d-flex justify-content-between align-items-center p-2 rounded bg-light border border-danger-subtle small"
              >
                <div>
                  {topic.kind === "test_type" ? (
                    <strong className="text-dark text-capitalize">
                      {topic.tag.replace(/_/g, " ")}
                    </strong>
                  ) : (
                    <span className="fw-bold text-dark">
                      <FormattedIon ionKeyOrTag={topic.tag} />
                    </span>
                  )}
                  <span className="text-muted ms-2">({topic.kind})</span>
                </div>
                <span className="badge bg-danger-subtle text-danger border border-danger-subtle font-monospace">
                  {t("result.questions_wrong", {
                    wrong: topic.wrong,
                    total: topic.total,
                  })}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Insights and Feedback */}
      {(insights.length > 0 || feedback.length > 0) && (
        <div className="card border-0 shadow-sm p-3 p-sm-4 mb-3 bg-white">
          {/* Feedback section */}
          {feedback.length > 0 && (
            <div className="mb-3">
              <h2 className="h6 fw-bold text-dark mb-2">
                📋 {t("result.feedback_title")}
              </h2>
              <div className="d-flex flex-column gap-2">
                {feedback.map((f, idx) => {
                  // Special formatting for feedback.weak_topic with radical
                  if (f.key === "feedback.weak_topic" && f.params?.kind === "radical") {
                    return (
                      <div key={idx} className="alert alert-secondary py-2 px-3 small mb-0">
                        {t("result.focus_on_radical")} <FormattedIon ionKeyOrTag={f.params.tag} />
                      </div>
                    );
                  }

                  const text = getTranslatedEntry(f.key, f.params);
                  if (!text) return null;
                  return (
                    <div key={idx} className="alert alert-light border py-2 px-3 small mb-0 text-dark">
                      {text}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Insights section */}
          {insights.length > 0 && (
            <div>
              <h2 className="h6 fw-bold text-dark mb-2">
                🔬 {t("result.insights_title")}
              </h2>
              <div className="d-flex flex-column gap-2">
                {insights.map((ins, idx) => {
                  // Special handling for insight.wrong_guess with ion chips
                  if (ins.key === "insight.wrong_guess") {
                    return (
                      <div
                        key={idx}
                        className="alert alert-light border py-2 px-3 small mb-0 d-flex flex-wrap align-items-center gap-2"
                      >
                        <span className="text-dark">{t("result.wrong_guess_label")}</span>
                        <div className="d-inline-flex gap-1">
                          {ins.params?.cat && (
                            <IonChip ionKey={ins.params.cat} type="cation" />
                          )}
                          {ins.params?.an && (
                            <IonChip ionKey={ins.params.an} type="anion" />
                          )}
                        </div>
                      </div>
                    );
                  }

                  const text = getTranslatedEntry(ins.key, ins.params);
                  if (!text) return null;
                  return (
                    <div key={idx} className="alert alert-light border py-2 px-3 small mb-0 text-dark">
                      💡 {text}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Detailed Question Review */}
      <div className="mb-4">
        <h2 className="h5 fw-bold mb-3">{t("result.review_title")}</h2>
        <div className="d-flex flex-column gap-3">
          {review.map((q, idx) => {
            const isCorrect = q.is_correct;
            const chosen = q.chosen;
            const correctAnswer = q.correct_answer;

            return (
              <div
                key={idx}
                className={`card border-0 shadow-sm p-3 bg-white ${
                  isCorrect
                    ? "border-start border-4 border-success"
                    : "border-start border-4 border-danger"
                }`}
              >
                {/* Question Position & Badges */}
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <div className="d-flex align-items-center gap-2">
                    <span className="badge bg-light text-muted border">
                      Q{q.position}
                    </span>
                    {q.source === "dynamic" && (
                      <span className="badge bg-info-subtle text-info border border-info-subtle small py-0">
                        🧪 {t("quiz.dynamic_tag")}
                      </span>
                    )}
                  </div>
                  <div>
                    {isCorrect ? (
                      <span className="badge bg-success-subtle text-success border border-success-subtle">
                        ✓ {t("result.correct")}
                      </span>
                    ) : (
                      <span className="badge bg-danger-subtle text-danger border border-danger-subtle">
                        ✗ {t("result.incorrect")}
                      </span>
                    )}
                  </div>
                </div>

                {/* Question Text */}
                <p className="fw-semibold text-dark mb-3" style={{ lineHeight: 1.35 }}>
                  {q.question}
                </p>

                {/* Options List */}
                <div className="d-flex flex-column gap-2 mb-3">
                  {q.options?.map((opt, optIdx) => {
                    const isUserChosen = opt === chosen;
                    const isOptionCorrect = opt === correctAnswer;

                    let optionClass = "bg-light text-muted border";
                    let labelBadge = null;

                    if (isOptionCorrect && isUserChosen) {
                      // Correctly chosen
                      optionClass = "bg-success-subtle border-success text-success-emphasis fw-bold";
                      labelBadge = (
                        <span className="badge bg-success text-white ms-auto">
                          ✓ {t("result.your_answer")}
                        </span>
                      );
                    } else if (isUserChosen && !isOptionCorrect) {
                      // Incorrectly chosen
                      optionClass = "bg-danger-subtle border-danger text-danger-emphasis fw-medium";
                      labelBadge = (
                        <span className="badge bg-danger text-white ms-auto">
                          ✗ {t("result.your_answer")}
                        </span>
                      );
                    } else if (isOptionCorrect && !isUserChosen) {
                      // Correct option that user missed
                      optionClass = "bg-white border-success text-success fw-bold";
                      labelBadge = (
                        <span className="badge bg-success-subtle text-success border border-success-subtle ms-auto">
                          ✓ {t("result.correct_answer")}
                        </span>
                      );
                    }

                    return (
                      <div
                        key={optIdx}
                        className={`p-2 rounded d-flex align-items-center small min-touch-target ${optionClass}`}
                      >
                        <span className="fw-bold me-2">
                          {String.fromCharCode(65 + optIdx)})
                        </span>
                        <span className="flex-grow-1">{opt}</span>
                        {labelBadge}
                      </div>
                    );
                  })}
                  {!chosen && (
                    <div className="text-danger small fst-italic">
                      ⚠️ {t("result.not_answered")}
                    </div>
                  )}
                </div>

                {/* Explanation */}
                {q.explanation && (
                  <div className="p-2 rounded bg-light border border-secondary-subtle small text-dark">
                    <strong>💡 {t("result.explanation")}:</strong> {q.explanation}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Practice Error Banner */}
      {practiceError && (
        <div className="alert alert-danger shadow-sm small py-2 px-3 mb-3">
          ⚠️ {practiceError}
        </div>
      )}

      {/* Action Buttons */}
      <div className="d-flex flex-column gap-2">
        {!is_practice && (
          <button
            type="button"
            className="btn btn-primary btn-lg w-100 min-touch-target fw-bold shadow-sm"
            disabled={startingPractice}
            onClick={handlePracticeAgain}
          >
            {startingPractice ? (
              <>
                <span
                  className="spinner-border spinner-border-sm me-2"
                  role="status"
                  aria-hidden="true"
                />
                {t("result.starting_practice")}
              </>
            ) : (
              t("result.practice_again")
            )}
          </button>
        )}

        <Link
          to="/"
          className="btn btn-outline-secondary btn-lg w-100 min-touch-target fw-medium"
        >
          {t("result.back_home")}
        </Link>
      </div>
    </div>
  );
}
