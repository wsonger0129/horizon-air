/**
 * Pi base URL for API and video.
 * When built for Pi (VITE_SERVE_FROM_PI=true), uses same origin so the app talks to the FastAPI backend on the same host.
 * Otherwise: Pi IP (default 192.168.50.1:5000 for legacy Flask). Override via env or localStorage.
 * Priority: window.HORIZON_PI_URL > localStorage horizon_pi_url > VITE_PI_BASE_URL > same-origin (Pi build) > default.
 */
const DEFAULT_PI_BASE_URL = 'http://192.168.50.1:5000';

function normalizeUrl(url) {
  if (!url || typeof url !== 'string') return '';
  return url.trim().replace(/\/+$/, '');
}

export function getPiBaseUrl() {
  if (typeof window !== 'undefined') {
    const winUrl = normalizeUrl(window.HORIZON_PI_URL);
    if (winUrl) return winUrl;
    try {
      const stored = normalizeUrl(localStorage.getItem('horizon_pi_url'));
      if (stored) return stored;
    } catch (_) {}
    // Built for Pi: frontend is served by FastAPI on same host — use same origin for API/stream
    if (import.meta.env?.VITE_SERVE_FROM_PI === 'true') {
      return window.location.origin;
    }
  }
  const env = import.meta.env?.VITE_PI_BASE_URL;
  if (env && typeof env === 'string') {
    const envUrl = normalizeUrl(env);
    if (envUrl) return envUrl;
  }
  return DEFAULT_PI_BASE_URL;
}

/** True if we should try to reach the Pi (e.g. in dev/demo mode). */
export function isPiConnectionEnabled() {
  return true;
}
