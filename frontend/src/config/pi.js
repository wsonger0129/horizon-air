/**
 * Pi base URL for API and video. Used when phone/laptop is on HorizonAir hotspot.
 * - Build-time: VITE_PI_BASE_URL (e.g. http://192.168.50.1:5000)
 * - Runtime: window.HORIZON_PI_URL overrides (for same LAN or different Pi IP)
 */
const DEFAULT_PI_BASE_URL = 'http://192.168.50.1:5000';

export function getPiBaseUrl() {
  if (typeof window !== 'undefined' && window.HORIZON_PI_URL) {
    const url = window.HORIZON_PI_URL.trim();
    if (url) return url.replace(/\/+$/, '');
  }
  const env = import.meta.env?.VITE_PI_BASE_URL;
  if (env && typeof env === 'string' && env.trim()) {
    return env.trim().replace(/\/+$/, '');
  }
  return DEFAULT_PI_BASE_URL;
}

/** True if we should try to reach the Pi (e.g. in dev/demo mode). */
export function isPiConnectionEnabled() {
  return true;
}
