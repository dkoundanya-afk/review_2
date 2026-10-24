/**
 * frontend/src/App.jsx
 * Application router and top-level provider setup.
 * Supported routes: /login, /register, /, /redeem, /quiz/:id, /result/:id, /badges, /history, /settings, /change-pin.
 */
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { SessionProvider } from "./session.jsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import PublicOnlyRoute from "./components/PublicOnlyRoute.jsx";
import TeacherRoute from "./components/TeacherRoute.jsx";
import AppLayout from "./components/AppLayout.jsx";
import TeacherLayout from "./components/TeacherLayout.jsx";

import LoginScreen from "./screens/LoginScreen.jsx";
import RegisterScreen from "./screens/RegisterScreen.jsx";
import ChangePinScreen from "./screens/ChangePinScreen.jsx";
import HomeScreen from "./screens/HomeScreen.jsx";
import RedeemScreen from "./screens/RedeemScreen.jsx";
import QuizScreen from "./screens/QuizScreen.jsx";
import ResultScreen from "./screens/ResultScreen.jsx";
import BadgesScreen from "./screens/BadgesScreen.jsx";
import HistoryScreen from "./screens/HistoryScreen.jsx";
import SettingsScreen from "./screens/SettingsScreen.jsx";
import TeacherClassesScreen from "./screens/TeacherClassesScreen.jsx";
import TeacherDashboardScreen from "./screens/TeacherDashboardScreen.jsx";
import TeacherGapsScreen from "./screens/TeacherGapsScreen.jsx";

export default function App() {
  return (
    <ErrorBoundary>
      <SessionProvider>
        <BrowserRouter>
          <Routes>
            {/* Public routes */}
            <Route
              path="/login"
              element={
                <PublicOnlyRoute>
                  <LoginScreen />
                </PublicOnlyRoute>
              }
            />
            <Route
              path="/register"
              element={
                <PublicOnlyRoute>
                  <RegisterScreen />
                </PublicOnlyRoute>
              }
            />

            {/* Student Protected routes */}
            <Route element={<ProtectedRoute />}>
              <Route path="/change-pin" element={<ChangePinScreen />} />

              <Route element={<AppLayout />}>
                <Route path="/" element={<HomeScreen />} />
                <Route path="/redeem" element={<RedeemScreen />} />
                <Route path="/quiz/:id" element={<QuizScreen />} />
                <Route path="/result/:id" element={<ResultScreen />} />
                <Route path="/badges" element={<BadgesScreen />} />
                <Route path="/history" element={<HistoryScreen />} />
                <Route path="/settings" element={<SettingsScreen />} />
              </Route>
            </Route>

            {/* Teacher Protected routes */}
            <Route element={<TeacherRoute />}>
              <Route element={<TeacherLayout />}>
                <Route path="/teacher" element={<Navigate to="/teacher/classes" replace />} />
                <Route path="/teacher/classes" element={<TeacherClassesScreen />} />
                <Route path="/teacher/classes/:id" element={<TeacherDashboardScreen />} />
                <Route path="/teacher/classes/:id/insights" element={<TeacherGapsScreen />} />
                <Route path="/teacher/classes/:id/gaps" element={<Navigate to={`/teacher/classes/:id/insights`} replace />} />
              </Route>
            </Route>

            {/* Fallback route */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </SessionProvider>
    </ErrorBoundary>
  );
}
