/**
 * frontend/src/components/AppLayout.jsx
 * Application layout shell containing TopBar, scrollable content area,
 * and fixed BottomNav.
 */
import { Outlet } from "react-router-dom";
import TopBar from "./TopBar.jsx";
import BottomNav from "./BottomNav.jsx";

export default function AppLayout() {
  return (
    <div className="app-shell d-flex flex-column min-vh-100">
      <TopBar />
      <main className="container-sm flex-grow-1 px-3 py-3 main-content">
        <Outlet />
      </main>
      <BottomNav />
    </div>
  );
}
