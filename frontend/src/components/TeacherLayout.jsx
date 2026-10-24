/**
 * frontend/src/components/TeacherLayout.jsx
 * Shell layout for the teacher portal.
 * Features top navigation bar, teacher identity badge, language toggle, and logout button.
 */
import { Link, Outlet, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useSession } from "../session.jsx";
import LanguageSelector from "./LanguageSelector.jsx";

export default function TeacherLayout() {
  const { t } = useTranslation();
  const { me, logout } = useSession();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="teacher-shell d-flex flex-column min-vh-100 bg-light">
      <header className="top-bar border-bottom bg-white sticky-top shadow-sm py-2 px-3">
        <div className="container-lg d-flex align-items-center justify-content-between p-0">
          <div className="d-flex align-items-center gap-2 gap-md-3">
            <Link to="/teacher/classes" className="text-decoration-none d-flex align-items-center gap-2">
              <span className="app-brand fw-bold text-primary fs-4">
                {t("app_name")}
              </span>
              <span className="badge bg-primary text-white px-2 py-1 small rounded-pill">
                {t("login.tab_teacher")}
              </span>
            </Link>
            <nav className="d-none d-md-flex align-items-center ms-3">
              <Link to="/teacher/classes" className="nav-link fw-semibold text-secondary px-2">
                {t("teacher_nav.classes")}
              </Link>
            </nav>
          </div>

          <div className="d-flex align-items-center gap-2">
            <span
              className="d-none d-sm-inline-block text-muted small fw-medium text-truncate"
              style={{ maxWidth: "220px" }}
              title={me?.display_name || me?.id}
            >
              👤 {me?.display_name || me?.id}
            </span>
            <LanguageSelector variant="compact" />
            <button
              type="button"
              className="btn btn-outline-danger btn-sm fw-semibold"
              onClick={handleLogout}
              aria-label={t("teacher_nav.logout")}
            >
              {t("teacher_nav.logout")}
            </button>
          </div>
        </div>
      </header>

      <main className="container-lg flex-grow-1 px-3 py-4">
        <Outlet />
      </main>
    </div>
  );
}
