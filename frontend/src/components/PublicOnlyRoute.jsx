/**
 * frontend/src/components/PublicOnlyRoute.jsx
 * Route wrapper that redirects authenticated users to the home dashboard
 * or change-pin screen.
 */
import { Navigate } from "react-router-dom";
import { useSession } from "../session.jsx";

export default function PublicOnlyRoute({ children }) {
  const { isAuthenticated, me } = useSession();

  if (isAuthenticated) {
    if (me?.role === "teacher") {
      return <Navigate to="/teacher/classes" replace />;
    }
    if (me?.must_change_pin) {
      return <Navigate to="/change-pin" replace />;
    }
    return <Navigate to="/" replace />;
  }

  return children;
}
