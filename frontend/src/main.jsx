/**
 * frontend/src/main.jsx
 * React entry point. Bootstrap CSS is imported here (npm package, no CDN).
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "bootstrap/dist/css/bootstrap.min.css";
import "./index.css";
import "./i18n.js";
import App from "./App.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>
);
