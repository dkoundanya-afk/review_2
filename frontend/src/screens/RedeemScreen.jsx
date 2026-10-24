/**
 * frontend/src/screens/RedeemScreen.jsx
 * Code redemption screen for Task U2.
 * Allows student to redeem a lab completion code + optional result token.
 * Features:
 *  - Monospace, auto-uppercase code input accepting pasted text with spaces
 *  - Live decoding preview of formula, name, and both ion chips
 *  - Multi-line optional token textarea
 *  - Comprehensive error mapping (including 429 wait time in minutes)
 *  - Success result card with formula, name, blue cation chip, orange anion chip
 *  - Token invalid gentle notice (still unlocked)
 *  - New badge toast
 *  - Start quiz action calling POST /quiz/start with friendly 404 fallback
 *  - Refreshes Home data on successful redemption
 */
import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import api, { getTranslatedError } from "../api.js";
import { FormattedFormula, IonChip } from "../components/IonDisplay.jsx";
import { decodeCompletionCode } from "../utils/chemistry.js";

export default function RedeemScreen() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();

  useEffect(() => {
    document.title = `${t("redeem.title")} — ${t("app_name")}`;
  }, [t, i18n.language]);

  const [code, setCode] = useState("");
  const [token, setToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successResult, setSuccessResult] = useState(null);
  const [startingQuiz, setStartingQuiz] = useState(false);
  const [quizNotice, setQuizNotice] = useState(null);

  // Live decoding preview as student types/pastes code
  const decodedPreview = decodeCompletionCode(code);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setQuizNotice(null);

    const cleanedCode = code.replace(/\s+/g, "").toUpperCase();
    if (!cleanedCode) {
      setError(t("errors.bad_format"));
      return;
    }

    setLoading(true);
    try {
      const res = await api.post("/redeem", {
        code: cleanedCode,
        token: token.trim() || undefined,
      });

      setSuccessResult(res);
      // Trigger background update for HomeScreen
      window.dispatchEvent(new CustomEvent("vl:refresh_progress"));
    } catch (err) {
      setError(getTranslatedError(t, err));
    } finally {
      setLoading(false);
    }
  };

  const handleStartQuiz = async (redemptionId) => {
    setStartingQuiz(true);
    setQuizNotice(null);
    try {
      const res = await api.post("/quiz/start", {
        redemption_id: redemptionId,
      });
      if (res?.attempt_id) {
        localStorage.setItem(`vl_quiz_redemption_${res.attempt_id}`, String(redemptionId));
        navigate(`/quiz/${res.attempt_id}`);
      }
    } catch {
      // Quiz backend is added in the next step: friendly notice on 404
      setQuizNotice(t("quiz.not_available_yet"));
    } finally {
      setStartingQuiz(false);
    }
  };

  const handleReset = () => {
    setCode("");
    setToken("");
    setError(null);
    setSuccessResult(null);
    setQuizNotice(null);
  };

  return (
    <div className="redeem-screen pb-5">
      {/* Top Header */}
      <div className="d-flex align-items-center mb-3">
        <Link
          to="/"
          className="btn btn-outline-secondary min-touch-target me-2 px-3 fw-medium"
        >
          &larr; {t("common.back")}
        </Link>
        <div>
          <h1 className="h4 fw-bold mb-0">{t("redeem.title")}</h1>
        </div>
      </div>

      {/* Quiz Notice (Friendly 404 alert) */}
      {quizNotice && (
        <div
          className="alert alert-info alert-dismissible fade show shadow-sm mb-3"
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

      {/* Error Alert */}
      {error && (
        <div
          className="alert alert-danger alert-dismissible fade show shadow-sm mb-3"
          role="alert"
        >
          <div className="d-flex align-items-center gap-2">
            <span>⚠️</span>
            <span>{error}</span>
          </div>
          <button
            type="button"
            className="btn-close ms-2"
            aria-label="Close"
            onClick={() => setError(null)}
          />
        </div>
      )}

      {!successResult ? (
        /* Redeem Input Form */
        <div className="card border-0 shadow-sm p-3 p-sm-4 bg-white">
          <p className="text-muted small mb-4">{t("redeem.subtitle")}</p>

          <form onSubmit={handleSubmit} noValidate>
            {/* Completion Code Input */}
            <div className="mb-3">
              <label htmlFor="code-input" className="form-label fw-bold small">
                {t("redeem.code_label")}{" "}
                <span className="text-danger">*</span>
              </label>
              <input
                id="code-input"
                type="text"
                className="form-control form-control-lg font-monospace text-uppercase fw-bold min-touch-target"
                placeholder={t("redeem.code_placeholder")}
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                autoComplete="off"
                spellCheck="false"
                required
              />
              <div className="form-text small">{t("redeem.code_help")}</div>

              {/* Live Decoding Preview if recognized */}
              {decodedPreview && (
                <div className="mt-2 p-2 rounded bg-light border border-primary-subtle d-flex flex-wrap align-items-center justify-content-between gap-2">
                  <div className="small">
                    <span className="text-muted me-1">{t("redeem.detected_salt")}</span>
                    <strong className="text-dark me-2">
                      <FormattedFormula formula={decodedPreview.formula} /> ({decodedPreview.name})
                    </strong>
                  </div>
                  <div className="d-flex gap-1">
                    <IonChip ionKey={decodedPreview.cationKey} type="cation" showName={false} />
                    <IonChip ionKey={decodedPreview.anionKey} type="anion" showName={false} />
                  </div>
                </div>
              )}
            </div>

            {/* Optional Result Token Input */}
            <div className="mb-4">
              <label htmlFor="token-input" className="form-label fw-bold small">
                {t("redeem.token_label")}
              </label>
              <textarea
                id="token-input"
                className="form-control font-monospace small"
                rows={3}
                placeholder={t("redeem.token_placeholder")}
                value={token}
                onChange={(e) => setToken(e.target.value)}
                autoComplete="off"
                spellCheck="false"
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              className="btn btn-primary btn-lg w-100 min-touch-target fw-bold shadow-sm"
              disabled={loading || !code.trim()}
            >
              {loading ? (
                <>
                  <span
                    className="spinner-border spinner-border-sm me-2"
                    role="status"
                    aria-hidden="true"
                  />
                  {t("redeem.redeeming")}
                </>
              ) : (
                t("redeem.submit")
              )}
            </button>
          </form>
        </div>
      ) : (
        /* Success Result Card */
        <div className="card border-0 shadow-sm p-4 bg-white text-center">
          {/* Badge Toast / Notification */}
          {successResult.new_badges && successResult.new_badges.length > 0 && (
            <div className="alert alert-success d-flex flex-column gap-2 mb-3 text-start shadow-sm">
              {successResult.new_badges.map((badge) => (
                <div key={badge.key} className="d-flex align-items-center gap-2">
                  <span className="fs-4" aria-hidden="true">🎉</span>
                  <div>
                    <strong className="d-block">
                      {t("redeem.new_badge_toast")}: {badge.name}
                    </strong>
                    <small className="text-success-emphasis">{badge.description}</small>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="mb-2">
            <span className="badge bg-success-subtle text-success border border-success-subtle px-3 py-2 fs-6">
              ✓ {successResult.already ? t("redeem.already_title") : t("redeem.success_title")}
            </span>
          </div>

          {/* Decoded Salt Formula & Plain Name */}
          <div className="my-3">
            <div className="fs-2 fw-bold text-dark mb-1">
              <FormattedFormula formula={successResult.formula} />
            </div>
            <div className="fs-5 text-muted fw-medium">{successResult.name}</div>
          </div>

          {/* Both Ion Chips: Blue for cation, Orange for anion */}
          <div className="d-flex justify-content-center gap-2 my-3">
            <IonChip ionKey={successResult.cation} type="cation" />
            <IonChip ionKey={successResult.anion} type="anion" />
          </div>

          {/* Explanation that Quiz is Unlocked */}
          <p className="text-dark fw-medium mb-3">
            {t("redeem.unlocked_sentence")}
          </p>

          {/* Gentle notice if token was provided but invalid */}
          {!successResult.token_valid && token.trim() && (
            <div className="alert alert-warning small text-start mb-3">
              <span>⚠️ {t("redeem.token_unusable_note")}</span>
            </div>
          )}

          {/* Action Buttons */}
          <div className="d-flex flex-column gap-2 mt-2">
            <button
              type="button"
              className="btn btn-primary btn-lg w-100 min-touch-target fw-bold shadow-sm"
              disabled={startingQuiz}
              onClick={() => handleStartQuiz(successResult.redemption_id)}
            >
              {startingQuiz ? (
                <>
                  <span
                    className="spinner-border spinner-border-sm me-2"
                    role="status"
                    aria-hidden="true"
                  />
                  {t("quiz.starting")}
                </>
              ) : (
                t("redeem.start_quiz")
              )}
            </button>

            <button
              type="button"
              className="btn btn-outline-secondary min-touch-target fw-medium"
              onClick={handleReset}
            >
              {t("redeem.redeem_another")}
            </button>

            <Link
              to="/"
              className="btn btn-link text-decoration-none min-touch-target"
            >
              {t("redeem.back_home")}
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
