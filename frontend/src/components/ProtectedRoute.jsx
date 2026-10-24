/**
 * frontend/src/components/ProtectedRoute.jsx
 * Enforces session authentication and handles forced PIN change state.
 */
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useSession } from "../session.jsx";

export default function ProtectedRoute() {
  const { isAuthenticated, me } = useSession();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // If a teacher navigates to student routes, redirect to teacher classes
  if (me?.role === "teacher") {
    return <Navigate to="/teacher/classes" replace />;
  }

  // If the server flagged must_change_pin, intercept and redirect to /change-pin
  if (me?.must_change_pin && location.pathname !== "/change-pin") {
    return <Navigate to="/change-pin" replace />;
  }

  return <Outlet />;
}
