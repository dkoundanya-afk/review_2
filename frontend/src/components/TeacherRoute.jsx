/**
 * frontend/src/components/TeacherRoute.jsx
 * Route guard enforcing teacher authentication.
 * Redirects unauthenticated visitors to /login.
 * Redirects authenticated students to the student portal (/)."
 */
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useSession } from "../session.jsx";

export default function TeacherRoute({ children }) {
  const { isAuthenticated, me } = useSession();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (me?.role !== "teacher") {
    return <Navigate to="/" replace />;
  }

  return children ? children : <Outlet />;
}
