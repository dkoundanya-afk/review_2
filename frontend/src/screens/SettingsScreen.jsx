/**
 * frontend/src/screens/SettingsScreen.jsx
 * Settings screen (Task U4).
 * Sections: Profile, Classes, Language, Security (change PIN inline), Logout.
 * Change PIN done inline without navigating away (uses the same API as ChangePinScreen).
 */
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useSession } from "../session.jsx";
import api, { getTranslatedError } from "../api.js";
import LanguageSelector from "../components/LanguageSelector.jsx";

export default function SettingsScreen() {
  const { t, i18n } = useTranslation();
  const { me, logout, updateMe } = useSession();

  useEffect(() => {
    document.title = `${t("settings.title")} — ${t("app_name")}`;
  }, [t, i18n.language]);

  // Inline change-PIN state
  const [showChangePin, setShowChangePin] = useState(false);
  const [oldPin, setOldPin] = useState("");
  const [newPin, setNewPin] = useState("");
  const [confirmPin, setConfirmPin] = useState("");
  const [pinError, setPinError] = useState("");
  const [pinSuccess, setPinSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const resetPinForm = () => {
    setOldPin("");
    setNewPin("");
    setConfirmPin("");
    setPinError("");
    setPinSuccess(false);
  };

  const handleChangePin = async (e) => {
    e.preventDefault();
    setPinError("");
    setPinSuccess(false);

    const cleanOld = oldPin.trim();
    const cleanNew = newPin.trim();
    const cleanConfirm = confirmPin.trim();

    if (!cleanOld) { setPinError(t("errors.wrong_current_pin")); return; }
    if (!cleanNew || !/^\d{4,6}$/.test(cleanNew)) { setPinError(t("errors.invalid_pin")); return; }
    if (cleanNew !== cleanConfirm) { setPinError(t("errors.pin_mismatch")); return; }

    setSubmitting(true);
    try {
      await api.post("/auth/change-pin", { old_pin: cleanOld, new_pin: cleanNew });
      updateMe({ must_change_pin: false });
      setPinSuccess(true);
      resetPinForm();
      setTimeout(() => { setShowChangePin(false); setPinSuccess(false); }, 2000);
    } catch (err) {
      setPinError(getTranslatedError(t, err));
    } finally {
      setSubmitting(false);
    }
  };

  const [loggingOut, setLoggingOut] = useState(false);
  const handleLogout = async () => {
    setLoggingOut(true);
    await logout();
  };

  const className = me?.classes && me.classes.length > 0
    ? me.classes.map((c) => c.name).join(", ")
    : null;

  return (
    <div className="settings-screen pb-5">
      <h1 className="h4 fw-bold mb-4">{t("settings.title")}</h1>

      {/* Profile Section */}
      <div className="card border-0 shadow-sm mb-3">
        <div className="card-header bg-transparent fw-semibold py-3 small text-uppercase text-muted">
          {t("settings.profile_section")}
        </div>
        <div className="card-body py-3">
          <div className="mb-3">
            <span className="text-muted small d-block mb-1">{t("settings.display_name")}</span>
            <span className="fw-semibold fs-6">{me?.display_name || "—"}</span>
          </div>
          <div className="mb-1">
            <span className="text-muted small d-block mb-1">{t("settings.student_id")}</span>
            <span className="font-monospace fw-semibold fs-6">{me?.id}</span>
          </div>
        </div>
      </div>

      {/* Enrolled Classes Section */}
      <div className="card border-0 shadow-sm mb-3">
        <div className="card-header bg-transparent fw-semibold py-3 small text-uppercase text-muted">
          {t("settings.classes_section")}
        </div>
        <div className="card-body py-3">
          {me?.classes && me.classes.length > 0 ? (
            <ul className="list-unstyled mb-0">
              {me.classes.map((cls) => (
                <li key={cls.id} className="py-1 fw-medium d-flex align-items-center gap-2">
                  <span aria-hidden="true">🏫</span> {cls.name}
                </li>
              ))}
            </ul>
          ) : (
            <span className="text-muted small">{t("settings.no_classes")}</span>
          )}
        </div>
      </div>

      {/* Language Section */}
      <div className="card border-0 shadow-sm mb-3">
        <div className="card-header bg-transparent fw-semibold py-3 small text-uppercase text-muted">
          {t("settings.language_section")}
        </div>
        <div className="card-body py-3">
          <LanguageSelector variant="buttons" />
        </div>
      </div>

      {/* Security Section */}
      <div className="card border-0 shadow-sm mb-4">
        <div className="card-header bg-transparent fw-semibold py-3 small text-uppercase text-muted">
          {t("settings.security_section")}
        </div>
        <div className="card-body py-3">
          {!showChangePin ? (
            <button
              type="button"
              className="btn btn-outline-primary w-100 fw-semibold min-touch-target"
              onClick={() => { resetPinForm(); setShowChangePin(true); }}
            >
              🔐 {t("settings.change_pin_btn")}
            </button>
          ) : (
            <form onSubmit={handleChangePin} noValidate>
              {pinSuccess && (
                <div className="alert alert-success py-2 px-3 small mb-3" role="status">
                  ✓ {t("change_pin.success")}
                </div>
              )}
              {pinError && (
                <div className="alert alert-danger py-2 px-3 small mb-3" role="alert">
                  {pinError}
                </div>
              )}

              <div className="mb-3">
                <label htmlFor="settings-old-pin" className="form-label fw-semibold small">
                  {t("change_pin.old_pin")}
                </label>
                <input
                  id="settings-old-pin"
                  type="password"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  className="form-control text-center font-monospace"
                  placeholder={t("change_pin.old_pin_placeholder")}
                  value={oldPin}
                  onChange={(e) => setOldPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  disabled={submitting}
                  autoComplete="current-password"
                  required
                />
              </div>

              <div className="mb-3">
                <label htmlFor="settings-new-pin" className="form-label fw-semibold small">
                  {t("change_pin.new_pin")}
                </label>
                <input
                  id="settings-new-pin"
                  type="password"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  className="form-control text-center font-monospace"
                  placeholder={t("change_pin.new_pin_placeholder")}
                  value={newPin}
                  onChange={(e) => setNewPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  disabled={submitting}
                  autoComplete="new-password"
                  required
                />
              </div>

              <div className="mb-3">
                <label htmlFor="settings-confirm-pin" className="form-label fw-semibold small">
                  {t("change_pin.confirm_new_pin")}
                </label>
                <input
                  id="settings-confirm-pin"
                  type="password"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  className="form-control text-center font-monospace"
                  placeholder={t("change_pin.confirm_new_pin_placeholder")}
                  value={confirmPin}
                  onChange={(e) => setConfirmPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  disabled={submitting}
                  autoComplete="new-password"
                  required
                />
              </div>

              <div className="d-flex gap-2">
                <button
                  type="submit"
                  className="btn btn-primary flex-grow-1 fw-bold min-touch-target"
                  disabled={submitting}
                >
                  {submitting ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true" />
                      {t("change_pin.updating")}
                    </>
                  ) : (
                    t("change_pin.submit")
                  )}
                </button>
                <button
                  type="button"
                  className="btn btn-outline-secondary min-touch-target"
                  disabled={submitting}
                  onClick={() => { setShowChangePin(false); resetPinForm(); }}
                >
                  {t("common.cancel")}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>

      {/* Logout */}
      <button
        type="button"
        className="btn btn-danger btn-lg w-100 fw-bold min-touch-target shadow-sm"
        disabled={loggingOut}
        onClick={handleLogout}
        aria-label={t("settings.logout_btn")}
      >
        {loggingOut ? (
          <>
            <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true" />
            {t("settings.logging_out")}
          </>
        ) : (
          `🚪 ${t("settings.logout_btn")}`
        )}
      </button>
    </div>
  );
}
