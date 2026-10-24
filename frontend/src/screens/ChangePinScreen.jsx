/**
 * frontend/src/screens/ChangePinScreen.jsx
 * Screen for students to change their PIN.
 * Required when me.must_change_pin is true or accessed via settings.
 */
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useSession } from "../session.jsx";
import api, { getTranslatedError } from "../api.js";

export default function ChangePinScreen() {
  const { t, i18n } = useTranslation();
  const { updateMe, logout } = useSession();
  const navigate = useNavigate();

  useEffect(() => {
    document.title = `${t("change_pin.title")} — ${t("app_name")}`;
  }, [t, i18n.language]);

  const [oldPin, setOldPin] = useState("");
  const [newPin, setNewPin] = useState("");
  const [confirmPin, setConfirmPin] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg("");

    const cleanOldPin = oldPin.trim();
    const cleanNewPin = newPin.trim();
    const cleanConfirm = confirmPin.trim();

    if (!cleanOldPin) {
      setErrorMsg(t("errors.wrong_current_pin"));
      return;
    }

    if (!cleanNewPin || !/^\d{4,6}$/.test(cleanNewPin)) {
      setErrorMsg(t("errors.invalid_pin"));
      return;
    }

    if (cleanNewPin !== cleanConfirm) {
      setErrorMsg(t("errors.pin_mismatch"));
      return;
    }

    setSubmitting(true);
    try {
      await api.post("/auth/change-pin", {
        old_pin: cleanOldPin,
        new_pin: cleanNewPin,
      });

      updateMe({ must_change_pin: false });
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
            <button
              type="button"
              className="btn btn-sm btn-outline-secondary"
              onClick={logout}
            >
              {t("settings.logout_btn")}
            </button>
          </div>

          <h1 className="h4 fw-bold mb-1">{t("change_pin.title")}</h1>
          <p className="text-muted small mb-4">{t("change_pin.subtitle")}</p>

          {errorMsg && (
            <div className="alert alert-danger py-2 px-3 small" role="alert">
              {errorMsg}
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>
            <div className="mb-3">
              <label htmlFor="change-old-pin" className="form-label fw-semibold small">
                {t("change_pin.old_pin")}
              </label>
              <input
                id="change-old-pin"
                type="password"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={6}
                className="form-control fs-6 text-center font-monospace"
                placeholder={t("change_pin.old_pin_placeholder")}
                value={oldPin}
                onChange={(e) => setOldPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
                disabled={submitting}
                required
              />
            </div>

            <div className="mb-3">
              <label htmlFor="change-new-pin" className="form-label fw-semibold small">
                {t("change_pin.new_pin")}
              </label>
              <input
                id="change-new-pin"
                type="password"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={6}
                className="form-control fs-6 text-center font-monospace"
                placeholder={t("change_pin.new_pin_placeholder")}
                value={newPin}
                onChange={(e) => setNewPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
                disabled={submitting}
                required
              />
            </div>

            <div className="mb-4">
              <label htmlFor="change-confirm-pin" className="form-label fw-semibold small">
                {t("change_pin.confirm_new_pin")}
              </label>
              <input
                id="change-confirm-pin"
                type="password"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={6}
                className="form-control fs-6 text-center font-monospace"
                placeholder={t("change_pin.confirm_new_pin_placeholder")}
                value={confirmPin}
                onChange={(e) => setConfirmPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
                disabled={submitting}
                required
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-lg w-100 fw-bold min-touch-target"
              disabled={submitting}
            >
              {submitting ? t("change_pin.updating") : t("change_pin.submit")}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
