/**
 * Pi base URL for API and video (live feed at /video_feed).
 * Default: Pi IP on HorizonAir network (aiPiCam.py Flask on port 5000). Override via env or localStorage if IP differs.
 * Priority: window.HORIZON_PI_URL > localStorage horizon_pi_url > VITE_PI_BASE_URL > default.
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
