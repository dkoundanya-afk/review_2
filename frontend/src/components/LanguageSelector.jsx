/**
 * frontend/src/components/LanguageSelector.jsx
 * Allows switching between English (en) and Kannada (kn).
 * Automatically synchronizes with server via PATCH /me/language when logged in.
 */
import { useTranslation } from "react-i18next";
import { useSession } from "../session.jsx";

export default function LanguageSelector({ variant = "compact" }) {
  const { i18n, t } = useTranslation();
  const { setLanguage } = useSession();

  const currentLang = i18n.language?.startsWith("kn") ? "kn" : "en";

  const handleChange = (e) => {
    const lang = e.target.value;
    setLanguage(lang);
  };

  const handleSelectLang = (lang) => {
    setLanguage(lang);
  };

  if (variant === "buttons") {
    return (
      <div className="btn-group" role="group" aria-label={t("common.language")}>
        <button
          type="button"
          className={`btn btn-sm ${currentLang === "en" ? "btn-primary" : "btn-outline-primary"}`}
          onClick={() => handleSelectLang("en")}
          aria-pressed={currentLang === "en"}
        >
          English
        </button>
        <button
          type="button"
          className={`btn btn-sm ${currentLang === "kn" ? "btn-primary" : "btn-outline-primary"}`}
          onClick={() => handleSelectLang("kn")}
          aria-pressed={currentLang === "kn"}
        >
          ಕನ್ನಡ
        </button>
      </div>
    );
  }

  return (
    <div className="language-selector-wrapper">
      <select
        className="form-select form-select-sm language-select"
        value={currentLang}
        onChange={handleChange}
        aria-label={t("common.language")}
      >
        <option value="en">English</option>
        <option value="kn">ಕನ್ನಡ</option>
      </select>
    </div>
  );
}
