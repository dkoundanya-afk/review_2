/**
 * frontend/src/components/BottomNav.jsx
 * Bottom navigation bar with Home, Badges, History, Settings.
 * Uses inline SVG icons (no external icon library).
 * Meets mobile touch target requirements (min 44px).
 */
import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";

export default function BottomNav() {
  const { t } = useTranslation();

  return (
    <nav className="bottom-nav border-top bg-white fixed-bottom shadow-lg" aria-label="Main Navigation">
      <div className="container-sm d-flex justify-content-around p-0">
        <NavLink
          to="/"
          end
          className={({ isActive }) => `bottom-nav-item ${isActive ? "active" : ""}`}
          aria-label={t("nav.home")}
        >
          <svg
            className="bottom-nav-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
            <polyline points="9 22 9 12 15 12 15 22" />
          </svg>
          <span className="bottom-nav-label">{t("nav.home")}</span>
        </NavLink>

        <NavLink
          to="/badges"
          className={({ isActive }) => `bottom-nav-item ${isActive ? "active" : ""}`}
          aria-label={t("nav.badges")}
        >
          <svg
            className="bottom-nav-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <circle cx="12" cy="8" r="6" />
            <path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11" />
          </svg>
          <span className="bottom-nav-label">{t("nav.badges")}</span>
        </NavLink>

        <NavLink
          to="/history"
          className={({ isActive }) => `bottom-nav-item ${isActive ? "active" : ""}`}
          aria-label={t("nav.history")}
        >
          <svg
            className="bottom-nav-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
          <span className="bottom-nav-label">{t("nav.history")}</span>
        </NavLink>

        <NavLink
          to="/settings"
          className={({ isActive }) => `bottom-nav-item ${isActive ? "active" : ""}`}
          aria-label={t("nav.settings")}
        >
          <svg
            className="bottom-nav-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
          <span className="bottom-nav-label">{t("nav.settings")}</span>
        </NavLink>
      </div>
    </nav>
  );
}
