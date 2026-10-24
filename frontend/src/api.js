/**
 * frontend/src/api.js
 * Fetch wrapper for VirtuLab backend API (/api).
 * Automatically injects Bearer token, parses {error}, throws {status, error, extra},
 * and clears session on 401.
 */

export class ApiError extends Error {
  constructor(status, error, extra = {}) {
    super(error);
    this.name = "ApiError";
    this.status = status;
    this.error = error;
    this.extra = extra;
  }
}

/**
 * Clear session credentials from local storage and notify listeners.
 */
export function clearStoredSession() {
  localStorage.removeItem("vl_token");
  localStorage.removeItem("vl_me");
  window.dispatchEvent(new CustomEvent("vl:session_cleared"));
}

/**
 * Retrieve the active auth token from localStorage.
 */
export function getStoredToken() {
  return localStorage.getItem("vl_token");
}

/**
 * Maps any error object or reason code to a translated message in the i18n catalogue.
 * Falls back to errors.generic_error if the code is unknown.
 */
export function getTranslatedError(t, err) {
  if (!err) return "";
  const code = typeof err === "string" ? err : err.error;
  if (!code) return t("errors.generic_error");

  if (code === "rate_limited") {
    const seconds = err?.extra?.retry_after ?? err?.retry_after;
    if (seconds) {
      const minutes = Math.max(1, Math.ceil(seconds / 60));
      return t("errors.rate_limited_with_minutes", { minutes });
    }
  }

  const key = `errors.${code}`;
  const translated = t(key);
  if (translated === key || !translated) {
    return t("errors.generic_error");
  }
  return translated;
}

/**
 * Central fetch wrapper for all API calls.
 */
export async function api(endpoint, options = {}) {
  const url = endpoint.startsWith("http")
    ? endpoint
    : endpoint.startsWith("/api")
    ? endpoint
    : `/api${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;

  const headers = new Headers(options.headers || {});

  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  // Inject Bearer token if not explicitly excluded
  const token = getStoredToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let body = options.body;
  if (body && typeof body === "object" && !(body instanceof FormData)) {
    if (!headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    body = JSON.stringify(body);
  }

  let res;
  try {
    res = await fetch(url, {
      ...options,
      headers,
      body,
    });
  } catch (netErr) {
    throw new ApiError(0, "network_error", { message: netErr.message });
  }

  // Handle 401 Unauthorized: clear session
  if (res.status === 401) {
    clearStoredSession();
  }

  let data = null;
  const contentType = res.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    try {
      data = await res.json();
    } catch {
      data = null;
    }
  }

  if (!res.ok) {
    const errorCode =
      data && data.error
        ? data.error
        : res.status === 429
        ? "rate_limited"
        : res.status === 401
        ? "not_authenticated"
        : "generic_error";

    throw new ApiError(res.status, errorCode, data || {});
  }

  return data;
}

// Convenience helpers
api.get = (url, options) => api(url, { ...options, method: "GET" });
api.post = (url, body, options) => api(url, { ...options, method: "POST", body });
api.patch = (url, body, options) => api(url, { ...options, method: "PATCH", body });
api.put = (url, body, options) => api(url, { ...options, method: "PUT", body });
api.delete = (url, options) => api(url, { ...options, method: "DELETE" });

/**
 * Triggers a secure authenticated file download from the API.
 * Uses Bearer authentication and creates a temporary blob download link.
 */
export async function downloadFile(endpoint, defaultFilename = "download.csv") {
  const url = endpoint.startsWith("http")
    ? endpoint
    : endpoint.startsWith("/api")
    ? endpoint
    : `/api${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;

  const headers = new Headers();
  const token = getStoredToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let res;
  try {
    res = await fetch(url, { headers });
  } catch (netErr) {
    throw new ApiError(0, "network_error", { message: netErr.message });
  }

  if (res.status === 401) {
    clearStoredSession();
    throw new ApiError(401, "not_authenticated");
  }

  if (!res.ok) {
    let errCode = "generic_error";
    try {
      const json = await res.json();
      if (json?.error) errCode = json.error;
    } catch {}
    throw new ApiError(res.status, errCode);
  }

  let filename = defaultFilename;
  const disposition = res.headers.get("content-disposition");
  if (disposition && disposition.includes("filename=")) {
    const match = disposition.match(/filename="?([^";]+)"?/);
    if (match && match[1]) {
      filename = match[1];
    }
  }

  const blob = await res.blob();
  const blobUrl = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(blobUrl);
  return filename;
}

api.download = downloadFile;

export default api;
