/**
 * frontend/src/components/TopBar.jsx
 * Top navigation bar showing App name and Language Selector.
 */
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import LanguageSelector from "./LanguageSelector.jsx";

export default function TopBar() {
  const { t } = useTranslation();

  return (
    <header className="top-bar border-bottom bg-white sticky-top shadow-sm py-2 px-3">
      <div className="container-sm d-flex align-items-center justify-content-between p-0">
        <Link to="/" className="text-decoration-none d-flex align-items-center gap-2">
          <span className="app-brand fw-bold text-primary fs-4">
            {t("app_name")}
          </span>
        </Link>
        <div className="d-flex align-items-center">
          <LanguageSelector variant="compact" />
        </div>
      </div>
    </header>
  );
}
