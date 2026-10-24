/**
 * frontend/src/screens/LoginScreen.jsx
 * Dual-mode login screen supporting Student (ID + PIN) and Teacher (Email + Password).
 * Student ID is stripped of spaces and uppercased before submit.
 * Teacher login redirects to /teacher/classes; student login redirects to / or /change-pin.
 */
import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useSession } from "../session.jsx";
import api, { getTranslatedError } from "../api.js";
import LanguageSelector from "../components/LanguageSelector.jsx";

export default function LoginScreen() {
  const { t, i18n } = useTranslation();
  const { login } = useSession();
  const navigate = useNavigate();

  const [role, setRole] = useState("student");
  const [studentId, setStudentId] = useState("");
  const [pin, setPin] = useState("");
  const [teacherEmail, setTeacherEmail] = useState("");
  const [teacherPassword, setTeacherPassword] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const titleKey = role === "teacher" ? "login.teacher_title" : "login.title";
    document.title = `${t(titleKey)} — ${t("app_name")}`;
  }, [t, i18n.language, role]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg("");

    let payload;
    if (role === "teacher") {
      const cleanEmail = teacherEmail.trim().toLowerCase();
      const cleanPassword = teacherPassword;

      if (!cleanEmail || !cleanEmail.includes("@") || !/\S+@\S+\.\S+/.test(cleanEmail)) {
        setErrorMsg(t("errors.invalid_email"));
        return;
      }

      if (!cleanPassword || cleanPassword.length < 8) {
        setErrorMsg(t("errors.invalid_password"));
        return;
      }

      payload = {
        identifier: cleanEmail,
        secret: cleanPassword,
      };
    } else {
      // Normalise student ID per portal rule: remove spaces, trim, uppercase
      const cleanSid = studentId.replace(/\s+/g, "").toUpperCase();
      const cleanPin = pin.trim();

      if (!cleanSid) {
        setErrorMsg(t("errors.invalid_student_id"));
        return;
      }

      if (!cleanPin || !/^\d{4,6}$/.test(cleanPin)) {
        setErrorMsg(t("errors.invalid_pin"));
        return;
      }

      payload = {
        identifier: cleanSid,
        secret: cleanPin,
      };
    }

    setSubmitting(true);
    try {
      const data = await api.post("/auth/login", payload);

      login(data.token, data.me);

      if (data.me?.role === "teacher") {
        navigate("/teacher/classes", { replace: true });
      } else if (data.me?.must_change_pin) {
        navigate("/change-pin", { replace: true });
      } else {
        navigate("/", { replace: true });
      }
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

          {/* Role selector tabs */}
          <div className="btn-group w-100 mb-3" role="tablist" aria-label="Login Mode">
            <button
              type="button"
              className={`btn fw-semibold py-2 ${role === "student" ? "btn-primary" : "btn-outline-primary"}`}
              onClick={() => { setRole("student"); setErrorMsg(""); }}
              id="tab-student"
              aria-selected={role === "student"}
            >
              {t("login.tab_student")}
            </button>
            <button
              type="button"
              className={`btn fw-semibold py-2 ${role === "teacher" ? "btn-primary" : "btn-outline-primary"}`}
              onClick={() => { setRole("teacher"); setErrorMsg(""); }}
              id="tab-teacher"
              aria-selected={role === "teacher"}
            >
              {t("login.tab_teacher")}
            </button>
          </div>

          <h1 className="h4 fw-bold mb-1">
            {role === "teacher" ? t("login.teacher_title") : t("login.title")}
          </h1>
          <p className="text-muted small mb-4">
            {role === "teacher" ? t("login.teacher_subtitle") : t("login.subtitle")}
          </p>

          {errorMsg && (
            <div className="alert alert-danger py-2 px-3 small" role="alert">
              {errorMsg}
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>
            {role === "student" ? (
              <>
                <div className="mb-3">
                  <label htmlFor="login-student-id" className="form-label fw-semibold small">
                    {t("login.student_id")}
                  </label>
                  <input
                    id="login-student-id"
                    type="text"
                    autoComplete="username"
                    className="form-control form-control-lg fs-6"
                    placeholder={t("login.student_id_placeholder")}
                    value={studentId}
                    onChange={(e) => setStudentId(e.target.value.toUpperCase())}
                    disabled={submitting}
                    required
                  />
                </div>

                <div className="mb-4">
                  <label htmlFor="login-pin" className="form-label fw-semibold small">
                    {t("login.pin")}
                  </label>
                  <input
                    id="login-pin"
                    type="password"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    maxLength={6}
                    autoComplete="current-password"
                    className="form-control form-control-lg fs-6 text-center font-monospace letter-spacing-2"
                    placeholder={t("login.pin_placeholder")}
                    value={pin}
                    onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
                    disabled={submitting}
                    required
                  />
                </div>
              </>
            ) : (
              <>
                <div className="mb-3">
                  <label htmlFor="login-teacher-email" className="form-label fw-semibold small">
                    {t("login.teacher_email")}
                  </label>
                  <input
                    id="login-teacher-email"
                    type="email"
                    autoComplete="email"
                    className="form-control form-control-lg fs-6"
                    placeholder={t("login.teacher_email_placeholder")}
                    value={teacherEmail}
                    onChange={(e) => setTeacherEmail(e.target.value)}
                    disabled={submitting}
                    required
                  />
                </div>

                <div className="mb-4">
                  <label htmlFor="login-teacher-password" className="form-label fw-semibold small">
                    {t("login.teacher_password")}
                  </label>
                  <input
                    id="login-teacher-password"
                    type="password"
                    autoComplete="current-password"
                    className="form-control form-control-lg fs-6"
                    placeholder={t("login.teacher_password_placeholder")}
                    value={teacherPassword}
                    onChange={(e) => setTeacherPassword(e.target.value)}
                    disabled={submitting}
                    required
                  />
                </div>
              </>
            )}

            <button
              type="submit"
              className="btn btn-primary btn-lg w-100 fw-bold min-touch-target"
              disabled={submitting}
            >
              {submitting ? t("login.logging_in") : t("login.submit")}
            </button>
          </form>

          {role === "student" ? (
            <div className="text-center mt-4 pt-2 border-top">
              <span className="text-muted small me-1">{t("login.no_account")}</span>
              <Link to="/register" className="small fw-semibold text-decoration-none">
                {t("login.register_link")}
              </Link>
            </div>
          ) : (
            <div className="text-center mt-4 pt-2 border-top">
              <span className="text-muted small">
                {t("login.teacher_no_account_note")}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
