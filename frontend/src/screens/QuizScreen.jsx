/**
 * frontend/src/screens/QuizScreen.jsx
 * Quiz screen for Task U3.
 * Features:
 *  - ONE question per screen.
 *  - Progress bar ("3 of 10").
 *  - Four large option buttons (min 44px tap targets).
 *  - Previous / Next buttons.
 *  - "From your experiment" tag on questions where source is "dynamic".
 *  - "Saved" indicator & immediate PUT /quiz/<id>/answers with time_ms.
 *  - Mirror answers in localStorage so refreshes / offline periods lose nothing.
 *  - Retry queue retried every 5s & on 'online' event with "Offline, will retry" banner.
 *  - Resume: start at the first unanswered question.
 *  - Last screen: review list of answered questions and Submit with confirmation dialog.
 *  - Submit sends ALL answers from local state and guards against double-tap.
 *  - Notice if no_lab_data is true.
 *  - If status is already "submitted", navigates directly to /result/:id.
 */
import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import api, { getTranslatedError } from "../api.js";
import { FormattedFormula } from "../components/IonDisplay.jsx";

export default function QuizScreen() {
  const { t, i18n } = useTranslation();
  const { id } = useParams();
  const navigate = useNavigate();

  useEffect(() => {
    document.title = `${t("quiz.title")} — ${t("app_name")}`;
  }, [t, i18n.language]);

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [quizData, setQuizData] = useState(null);

  // answers map: { [question_id]: { chosen: string, time_ms: number } }
  const [answers, setAnswers] = useState({});
  const [currentIndex, setCurrentIndex] = useState(0);

  // Save states: 'idle' | 'saving' | 'saved' | 'offline_retry'
  const [saveStatus, setSaveStatus] = useState("idle");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  // Time tracking ref & retry queue
  const retryQueueRef = useRef({}); // { [qid]: { question_id, chosen, time_ms } }
  const focusStartTimeRef = useRef(0);
  const storageKey = `vl_quiz_answers_${id}`;

  // Flush retry queue helper
  const flushRetryQueue = useCallback(async () => {
    const items = Object.values(retryQueueRef.current);
    if (items.length === 0) return;

    try {
      await api.put(`/quiz/${id}/answers`, { answers: items });
      retryQueueRef.current = {};
      setSaveStatus("saved");
    } catch {
      setSaveStatus("offline_retry");
    }
  }, [id]);

  // Periodic retry & online listener
  useEffect(() => {
    const interval = setInterval(() => {
      if (Object.keys(retryQueueRef.current).length > 0) {
        flushRetryQueue();
      }
    }, 5000);

    const handleOnline = () => {
      if (Object.keys(retryQueueRef.current).length > 0) {
        flushRetryQueue();
      }
    };

    window.addEventListener("online", handleOnline);

    return () => {
      clearInterval(interval);
      window.removeEventListener("online", handleOnline);
    };
  }, [flushRetryQueue]);

  // Initial load
  useEffect(() => {
    let isMounted = true;

    async function loadQuiz() {
      setLoading(true);
      setLoadError(null);

      try {
        const data = await api.get(`/quiz/${id}`);
        if (!isMounted) return;

        // If already submitted, navigate straight to result
        if (data.status === "submitted") {
          navigate(`/result/${id}`, { replace: true });
          return;
        }

        setQuizData(data);

        // Read stored answers from localStorage
        let localAnswers = {};
        try {
          const raw = localStorage.getItem(storageKey);
          if (raw) localAnswers = JSON.parse(raw);
        } catch {
          localAnswers = {};
        }

        // Merge server answers and local answers
        const merged = {};
        if (data.answers && typeof data.answers === "object") {
          Object.entries(data.answers).forEach(([qid, chosen]) => {
            if (chosen) {
              merged[qid] = { chosen, time_ms: 0 };
            }
          });
        }
        if (localAnswers && typeof localAnswers === "object") {
          Object.entries(localAnswers).forEach(([qid, item]) => {
            if (item && item.chosen) {
              merged[qid] = { chosen: item.chosen, time_ms: item.time_ms || 0 };
            }
          });
        }

        setAnswers(merged);

        // Resume: start at the first unanswered question
        const sortedQs = [...(data.questions || [])].sort((a, b) => a.position - b.position);
        const firstUnanswered = sortedQs.findIndex((q) => !merged[q.id]?.chosen);

        if (firstUnanswered !== -1) {
          setCurrentIndex(firstUnanswered);
        } else {
          // If all are answered, start at the review screen
          setCurrentIndex(sortedQs.length);
        }

        focusStartTimeRef.current = Date.now();
        setLoading(false);
      } catch (err) {
        if (!isMounted) return;
        setLoadError(getTranslatedError(t, err));
        setLoading(false);
      }
    }

    loadQuiz();

    return () => {
      isMounted = false;
    };
  }, [id, navigate, storageKey, t]);

  // Handle option selection
  const handleSelectOption = async (questionId, optionText) => {
    if (isSubmitting) return;

    const now = Date.now();
    const elapsed = Math.max(0, now - focusStartTimeRef.current);
    focusStartTimeRef.current = now;

    const existingTime = answers[questionId]?.time_ms || 0;
    const newTimeMs = existingTime + elapsed;

    const updatedAnswers = {
      ...answers,
      [questionId]: {
        chosen: optionText,
        time_ms: newTimeMs,
      },
    };

    setAnswers(updatedAnswers);

    // Mirror to localStorage immediately
    try {
      localStorage.setItem(storageKey, JSON.stringify(updatedAnswers));
    } catch (e) {
      console.warn("Could not save to localStorage", e);
    }

    // Immediate autosave to backend
    setSaveStatus("saving");
    const payloadItem = {
      question_id: questionId,
      chosen: optionText,
      time_ms: newTimeMs,
    };

    try {
      await api.put(`/quiz/${id}/answers`, { answers: [payloadItem] });
      delete retryQueueRef.current[questionId];
      setSaveStatus("saved");
    } catch {
      // Put in retry queue and mark offline_retry
      retryQueueRef.current[questionId] = payloadItem;
      setSaveStatus("offline_retry");
    }
  };

  // Switch questions
  const goToQuestion = (idx) => {
    // Record elapsed time for current question before switching
    const currentQ = quizData?.questions?.[currentIndex];
    if (currentQ) {
      const now = Date.now();
      const elapsed = Math.max(0, now - focusStartTimeRef.current);
      if (elapsed > 0 && answers[currentQ.id]) {
        setAnswers((prev) => ({
          ...prev,
          [currentQ.id]: {
            ...prev[currentQ.id],
            time_ms: (prev[currentQ.id].time_ms || 0) + elapsed,
          },
        }));
      }
    }

    focusStartTimeRef.current = Date.now();
    setCurrentIndex(idx);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  // Submit quiz handler
  const handleSubmitQuiz = async () => {
    if (isSubmitting) return;
    setIsSubmitting(true);
    setSubmitError(null);
    setShowConfirmModal(false);

    // Record time on active question if on one
    const currentQ = quizData?.questions?.[currentIndex];
    const now = Date.now();
    const elapsed = Math.max(0, now - focusStartTimeRef.current);

    const finalAnswersMap = { ...answers };
    if (currentQ && finalAnswersMap[currentQ.id]) {
      finalAnswersMap[currentQ.id] = {
        ...finalAnswersMap[currentQ.id],
        time_ms: (finalAnswersMap[currentQ.id].time_ms || 0) + elapsed,
      };
    }

    // Format all answers
    const allAnswersPayload = Object.entries(finalAnswersMap).map(([qid, val]) => ({
      question_id: Number(qid),
      chosen: val.chosen,
      time_ms: val.time_ms || 0,
    }));

    try {
      await api.post(`/quiz/${id}/submit`, { answers: allAnswersPayload });
      // Clear localStorage answers on successful submission
      try {
        localStorage.removeItem(storageKey);
      } catch {
        // Ignore storage errors
      }
      retryQueueRef.current = {};
      navigate(`/result/${id}`);
    } catch (err) {
      setSubmitError(getTranslatedError(t, err) || t("quiz.error_submitting"));
      setIsSubmitting(false);
    }
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
      <div className="quiz-error py-4">
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

  const questions = quizData?.questions || [];
  const totalQuestions = questions.length;
  const isReviewScreen = currentIndex >= totalQuestions;
  const currentQuestion = questions[currentIndex];

  const answeredCount = questions.filter((q) => Boolean(answers[q.id]?.chosen)).length;
  const unansweredCount = totalQuestions - answeredCount;

  return (
    <div className="quiz-screen pb-5">
      {/* Top Header */}
      <div className="d-flex align-items-center justify-content-between mb-2">
        <div className="d-flex align-items-center gap-2">
          <Link
            to="/"
            className="btn btn-sm btn-outline-secondary min-touch-target px-2 py-1"
            title={t("common.back")}
            aria-label={t("common.back")}
          >
            &larr;
          </Link>
          <div>
            <h1 className="h5 fw-bold mb-0">
              <FormattedFormula formula={quizData?.formula} /> ({quizData?.name})
            </h1>
            {quizData?.is_practice && (
              <span className="badge bg-secondary-subtle text-secondary border border-secondary-subtle font-monospace py-0">
                {t("result.practice_mode")}
              </span>
            )}
          </div>
        </div>

        {/* Saved Status Indicator */}
        <div className="d-flex align-items-center">
          {saveStatus === "saving" && (
            <span className="badge bg-light text-muted border">
              <span className="spinner-border spinner-border-sm me-1" role="status" />
              {t("quiz.saving")}
            </span>
          )}
          {saveStatus === "saved" && (
            <span className="badge bg-success-subtle text-success border border-success-subtle">
              ✓ {t("quiz.saved")}
            </span>
          )}
          {saveStatus === "offline_retry" && (
            <span className="badge bg-warning-subtle text-warning border border-warning-subtle">
              ⚠️ {t("quiz.offline_retry")}
            </span>
          )}
        </div>
      </div>

      {/* Offline Alert Banner */}
      {saveStatus === "offline_retry" && (
        <div className="alert alert-warning py-2 px-3 small d-flex align-items-center justify-content-between mb-3 shadow-sm">
          <span>⚠️ {t("quiz.offline_retry")}</span>
          <button
            type="button"
            className="btn btn-sm btn-outline-dark py-0 min-touch-target"
            onClick={flushRetryQueue}
          >
            {t("quiz.retry_now")}
          </button>
        </div>
      )}

      {/* Lab Data Not Available Notice */}
      {quizData?.no_lab_data && (
        <div className="alert alert-info py-2 px-3 small mb-3 shadow-sm">
          ℹ️ {t("quiz.no_lab_data_notice")}
        </div>
      )}

      {/* Progress Bar & Counter */}
      <div className="mb-3">
        <div className="d-flex justify-content-between align-items-center small text-muted mb-1">
          <span>
            {isReviewScreen
              ? t("quiz.review_title")
              : t("quiz.progress", {
                  current: currentIndex + 1,
                  total: totalQuestions,
                })}
          </span>
          <span className="fw-medium">
            {t("quiz.answered_count", {
              answered: answeredCount,
              total: totalQuestions,
            })}
          </span>
        </div>
        <div className="progress" style={{ height: "8px" }}>
          <div
            className="progress-bar bg-primary"
            role="progressbar"
            style={{
              width: `${(answeredCount / (totalQuestions || 1)) * 100}%`,
            }}
            aria-valuenow={answeredCount}
            aria-valuemin={0}
            aria-valuemax={totalQuestions}
          />
        </div>
      </div>

      {/* Screen Content: Single Question vs Review Screen */}
      {!isReviewScreen && currentQuestion ? (
        <div className="question-card card border-0 shadow-sm p-3 p-sm-4 mb-4">
          {/* Question Source / Dynamic Tag */}
          <div className="d-flex justify-content-between align-items-center mb-2">
            <span className="badge bg-light text-muted border">
              {t("quiz.question_num", { num: currentQuestion.position })}
            </span>
            {currentQuestion.source === "dynamic" && (
              <span className="badge bg-info-subtle text-info border border-info-subtle fw-semibold">
                🧪 {t("quiz.dynamic_tag")}
              </span>
            )}
          </div>

          {/* Question Text */}
          <h2 className="h5 fw-bold text-dark my-3" style={{ lineHeight: 1.4 }}>
            {currentQuestion.question}
          </h2>

          {/* Four Large Option Buttons */}
          <div className="d-flex flex-column gap-2 my-2">
            {currentQuestion.options?.map((optionText, optIdx) => {
              const isSelected = answers[currentQuestion.id]?.chosen === optionText;

              return (
                <button
                  key={optIdx}
                  type="button"
                  onClick={() => handleSelectOption(currentQuestion.id, optionText)}
                  className={`btn text-start p-3 min-touch-target fw-medium shadow-sm transition-all ${
                    isSelected
                      ? "btn-primary border-2 shadow"
                      : "btn-outline-secondary bg-white text-dark border"
                  }`}
                  style={{
                    borderRadius: "10px",
                    fontSize: "0.95rem",
                    lineHeight: "1.35",
                  }}
                >
                  <div className="d-flex align-items-start gap-2">
                    <span
                      className={`badge rounded-circle p-1 me-1 ${
                        isSelected ? "bg-white text-primary" : "bg-light text-muted border"
                      }`}
                      style={{ width: "24px", height: "24px", textAlign: "center" }}
                    >
                      {String.fromCharCode(65 + optIdx)}
                    </span>
                    <span className="flex-grow-1">{optionText}</span>
                    {isSelected && <span className="fs-6">✓</span>}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Navigation Controls */}
          <div className="d-flex justify-content-between align-items-center mt-4 pt-2 border-top">
            <button
              type="button"
              className="btn btn-outline-secondary min-touch-target px-3 fw-medium"
              disabled={currentIndex === 0}
              onClick={() => goToQuestion(currentIndex - 1)}
            >
              &larr; {t("quiz.previous")}
            </button>

            {currentIndex < totalQuestions - 1 ? (
              <button
                type="button"
                className="btn btn-primary min-touch-target px-4 fw-medium"
                onClick={() => goToQuestion(currentIndex + 1)}
              >
                {t("quiz.next")} &rarr;
              </button>
            ) : (
              <button
                type="button"
                className="btn btn-success min-touch-target px-3 fw-medium"
                onClick={() => goToQuestion(totalQuestions)}
              >
                {t("quiz.review_submit")} &rarr;
              </button>
            )}
          </div>
        </div>
      ) : (
        /* Review Screen */
        <div className="review-screen card border-0 shadow-sm p-3 p-sm-4 mb-4">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <div>
              <h2 className="h5 fw-bold mb-1">{t("quiz.review_title")}</h2>
              <p className="text-muted small mb-0">{t("quiz.review_subtitle")}</p>
            </div>
            <span
              className={`badge px-2 py-1 fs-6 ${
                unansweredCount === 0 ? "bg-success" : "bg-warning text-dark"
              }`}
            >
              {unansweredCount === 0
                ? t("quiz.all_answered")
                : t("quiz.n_unanswered", { count: unansweredCount })}
            </span>
          </div>

          {/* Submit Error Banner if any */}
          {submitError && (
            <div className="alert alert-danger shadow-sm py-2 px-3 small mb-3">
              ⚠️ {submitError}
            </div>
          )}

          {/* Review List of all questions */}
          <div className="list-group list-group-flush mb-4">
            {questions.map((q, idx) => {
              const isAnswered = Boolean(answers[q.id]?.chosen);
              const chosenText = answers[q.id]?.chosen;

              return (
                <div
                  key={q.id}
                  onClick={() => goToQuestion(idx)}
                  className="list-group-item list-group-item-action d-flex justify-content-between align-items-center py-3 px-2 cursor-pointer border-bottom"
                >
                  <div className="me-2" style={{ maxWidth: "75%" }}>
                    <div className="d-flex align-items-center gap-2 mb-1">
                      <span className="badge bg-light text-dark border">
                        Q{q.position}
                      </span>
                      {q.source === "dynamic" && (
                        <span className="badge bg-info-subtle text-info border border-info-subtle small py-0">
                          🧪 {t("quiz.dynamic_tag")}
                        </span>
                      )}
                    </div>
                    <div className="small fw-semibold text-truncate mb-1">
                      {q.question}
                    </div>
                    {isAnswered ? (
                      <div className="small text-muted text-truncate">
                        <em>{chosenText}</em>
                      </div>
                    ) : (
                      <div className="small text-danger fw-medium">
                        {t("quiz.status_unanswered")}
                      </div>
                    )}
                  </div>

                  <div>
                    {isAnswered ? (
                      <span className="badge bg-success-subtle text-success border border-success-subtle">
                        ✓ {t("quiz.status_answered")}
                      </span>
                    ) : (
                      <button
                        type="button"
                        className="btn btn-sm btn-outline-warning text-dark min-touch-target py-1 px-2"
                        onClick={(e) => {
                          e.stopPropagation();
                          goToQuestion(idx);
                        }}
                      >
                        {t("quiz.answer_btn")}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Review Screen Actions */}
          <div className="d-flex flex-column gap-2 mt-2">
            <button
              type="button"
              className="btn btn-primary btn-lg w-100 min-touch-target fw-bold shadow-sm"
              disabled={isSubmitting}
              onClick={() => setShowConfirmModal(true)}
            >
              {isSubmitting ? (
                <>
                  <span
                    className="spinner-border spinner-border-sm me-2"
                    role="status"
                    aria-hidden="true"
                  />
                  {t("quiz.submitting")}
                </>
              ) : (
                t("quiz.submit_btn")
              )}
            </button>

            <button
              type="button"
              className="btn btn-outline-secondary min-touch-target"
              disabled={isSubmitting}
              onClick={() => goToQuestion(0)}
            >
              &larr; {t("quiz.jump_to_question")} 1
            </button>
          </div>
        </div>
      )}

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <div
          className="modal fade show d-block"
          tabIndex="-1"
          style={{ backgroundColor: "rgba(0,0,0,0.5)" }}
          role="dialog"
          aria-modal="true"
        >
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content border-0 shadow">
              <div className="modal-header">
                <h5 className="modal-title fw-bold">{t("quiz.confirm_title")}</h5>
                <button
                  type="button"
                  className="btn-close"
                  aria-label="Close"
                  disabled={isSubmitting}
                  onClick={() => setShowConfirmModal(false)}
                />
              </div>
              <div className="modal-body py-3">
                {unansweredCount > 0 ? (
                  <div className="alert alert-warning mb-0">
                    <strong>⚠️ {t("quiz.confirm_unanswered", { unanswered: unansweredCount })}</strong>
                  </div>
                ) : (
                  <p className="mb-0 text-dark">
                    {t("quiz.confirm_all", { total: totalQuestions })}
                  </p>
                )}
              </div>
              <div className="modal-footer flex-nowrap gap-2">
                <button
                  type="button"
                  className="btn btn-outline-secondary w-50 min-touch-target"
                  disabled={isSubmitting}
                  onClick={() => setShowConfirmModal(false)}
                >
                  {t("quiz.confirm_cancel")}
                </button>
                <button
                  type="button"
                  className={`btn w-50 min-touch-target fw-bold ${
                    unansweredCount > 0 ? "btn-danger" : "btn-primary"
                  }`}
                  disabled={isSubmitting}
                  onClick={handleSubmitQuiz}
                >
                  {isSubmitting ? (
                    <span className="spinner-border spinner-border-sm" role="status" />
                  ) : (
                    t("quiz.confirm_submit")
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
