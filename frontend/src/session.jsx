/**
 * frontend/src/session.jsx
 * Authentication and user session state via React Context and localStorage.
 */
import { createContext, useContext, useEffect, useState, useCallback } from "react";
import api, { clearStoredSession } from "./api.js";
import i18n from "./i18n.js";

const SessionContext = createContext(null);

export function SessionProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("vl_token"));
  const [me, setMe] = useState(() => {
    const raw = localStorage.getItem("vl_me");
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  });
  const [loading] = useState(false);

  // Sync session changes from api.js 401 handler
  useEffect(() => {
    const handleCleared = () => {
      setToken(null);
      setMe(null);
    };
    window.addEventListener("vl:session_cleared", handleCleared);
    return () => window.removeEventListener("vl:session_cleared", handleCleared);
  }, []);

  // When session is active on load, ensure i18n language matches profile if set
  useEffect(() => {
    if (me?.lang && me.lang !== i18n.language) {
      i18n.changeLanguage(me.lang);
      localStorage.setItem("vl_lang", me.lang);
    }
  }, [me?.lang]);

  const login = useCallback((newToken, newMe) => {
    localStorage.setItem("vl_token", newToken);
    localStorage.setItem("vl_me", JSON.stringify(newMe));
    setToken(newToken);
    setMe(newMe);
    if (newMe?.lang) {
      i18n.changeLanguage(newMe.lang);
      localStorage.setItem("vl_lang", newMe.lang);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } catch {
      // Ignore network / token error on logout
    } finally {
      clearStoredSession();
      setToken(null);
      setMe(null);
    }
  }, []);

  const updateMe = useCallback((partial) => {
    setMe((prev) => {
      const next = prev ? { ...prev, ...partial } : partial;
      localStorage.setItem("vl_me", JSON.stringify(next));
      return next;
    });
  }, []);

  const setLanguage = useCallback(
    async (lang) => {
      i18n.changeLanguage(lang);
      localStorage.setItem("vl_lang", lang);
      if (token) {
        try {
          const res = await api.patch("/me/language", { lang });
          updateMe({ lang: res.lang });
        } catch {
          // If language patch fails, local switch still holds
        }
      }
    },
    [token, updateMe]
  );

  const value = {
    token,
    me,
    isAuthenticated: Boolean(token && me),
    loading,
    login,
    logout,
    updateMe,
    setLanguage,
  };

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) {
    throw new Error("useSession must be used within a SessionProvider");
  }
  return ctx;
}

export default SessionContext;
