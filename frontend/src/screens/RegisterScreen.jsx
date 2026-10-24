/**
 * frontend/src/screens/RegisterScreen.jsx
 * Student registration screen.
 * Fields: Student ID, Class Join Code, Display Name (optional), PIN twice.
 */
import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useSession } from "../session.jsx";
import api, { getTranslatedError } from "../api.js";
import LanguageSelector from "../components/LanguageSelector.jsx";

export default function RegisterScreen() {
  const { t, i18n } = useTranslation();
  const { login } = useSession();
  const navigate = useNavigate();

  useEffect(() => {
    document.title = `${t("register.title")} — ${t("app_name")}`;
  }, [t, i18n.language]);

  const [studentId, setStudentId] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [pin, setPin] = useState("");
  const [confirmPin, setConfirmPin] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg("");

    const cleanSid = studentId.replace(/\s+/g, "").toUpperCase();
    const cleanJoinCode = joinCode.replace(/\s+/g, "").toUpperCase();
    const cleanPin = pin.trim();
    const cleanConfirmPin = confirmPin.trim();

    if (!cleanSid) {
      setErrorMsg(t("errors.invalid_student_id"));
      return;
    }

    if (!cleanJoinCode) {
      setErrorMsg(t("errors.invalid_join_code"));
      return;
    }

    if (!cleanPin || !/^\d{4,6}$/.test(cleanPin)) {
      setErrorMsg(t("errors.invalid_pin"));
      return;
    }

    if (cleanPin !== cleanConfirmPin) {
      setErrorMsg(t("errors.pin_mismatch"));
      return;
    }

    setSubmitting(true);
    try {
      const data = await api.post("/auth/register", {
        student_id: cleanSid,
        join_code: cleanJoinCode,
        pin: cleanPin,
        display_name: displayName.trim(),
      });

      login(data.token, data.me);
      navigate("/", { replace: true });
    } catch (err) {
      setErrorMsg(getTranslatedError(t, err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-container d-flex flex-column min-vh-100 justify-content-center py-4 px-3">
      <div className="auth-card card mx-auto shadow-sm border-0 w-100" style={{ maxWidth: "420px" }}>
        <div className="card-body p-4">
          <div className="d-flex justify-content-between align-items-center mb-4">
            <span className="app-brand fw-bold text-primary fs-4">{t("app_name")}</span>
            <LanguageSelector variant="compact" />
          </div>

          <h1 className="h4 fw-bold mb-1">{t("register.title")}</h1>
          <p className="text-muted small mb-4">{t("register.subtitle")}</p>

          {errorMsg && (
            <div className="alert alert-danger py-2 px-3 small" role="alert">
              {errorMsg}
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>
            <div className="mb-3">
              <label htmlFor="reg-student-id" className="form-label fw-semibold small">
                {t("register.student_id")}
              </label>
              <input
                id="reg-student-id"
                type="text"
                autoComplete="username"
                className="form-control fs-6"
                placeholder={t("register.student_id_placeholder")}
                value={studentId}
                onChange={(e) => setStudentId(e.target.value.toUpperCase())}
                disabled={submitting}
                required
              />
              <div className="form-text small">{t("register.student_id_help")}</div>
            </div>

            <div className="mb-3">
              <label htmlFor="reg-join-code" className="form-label fw-semibold small">
                {t("register.join_code")}
              </label>
              <input
                id="reg-join-code"
                type="text"
                className="form-control fs-6 font-monospace"
                placeholder={t("register.join_code_placeholder")}
                value={joinCode}
                onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                disabled={submitting}
                required
              />
            </div>

            <div className="mb-3">
              <label htmlFor="reg-display-name" className="form-label fw-semibold small">
                {t("register.display_name")}
              </label>
              <input
                id="reg-display-name"
                type="text"
                className="form-control fs-6"
                placeholder={t("register.display_name_placeholder")}
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                disabled={submitting}
              />
            </div>

            <div className="row g-2 mb-4">
              <div className="col-6">
                <label htmlFor="reg-pin" className="form-label fw-semibold small">
                  {t("register.pin")}
                </label>
                <input
                  id="reg-pin"
                  type="password"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  className="form-control fs-6 text-center font-monospace"
                  placeholder={t("register.pin_placeholder")}
                  value={pin}
                  onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  disabled={submitting}
                  required
                />
              </div>
              <div className="col-6">
                <label htmlFor="reg-confirm-pin" className="form-label fw-semibold small">
                  {t("register.confirm_pin")}
                </label>
                <input
                  id="reg-confirm-pin"
                  type="password"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  className="form-control fs-6 text-center font-monospace"
                  placeholder={t("register.confirm_pin_placeholder")}
                  value={confirmPin}
                  onChange={(e) => setConfirmPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  disabled={submitting}
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-lg w-100 fw-bold min-touch-target"
              disabled={submitting}
            >
              {submitting ? t("register.registering") : t("register.submit")}
            </button>
          </form>

          <div className="text-center mt-4 pt-2 border-top">
            <span className="text-muted small me-1">{t("register.have_account")}</span>
            <Link to="/login" className="small fw-semibold text-decoration-none">
              {t("register.login_link")}
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
