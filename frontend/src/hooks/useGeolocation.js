import { useState, useCallback, useEffect } from 'react';

/**
 * Geolocation for GPS-based navigation. Safari requires HTTPS (secure context) to prompt for location.
 * Call requestLocation() to trigger the browser's "Allow location?" prompt (e.g. from a button).
 */
export function useGeolocation(options = {}) {
  const { enableHighAccuracy = true, timeout = 15000, maximumAge = 10000 } = options;
  const [position, setPosition] = useState(null);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState('idle'); // idle | requesting | allowed | denied | unavailable | error

  const isSecureContext =
    typeof window !== 'undefined' &&
    (window.isSecureContext ?? (window.location?.protocol === 'https:' || window.location?.hostname === 'localhost'));

  const requestLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setError('Geolocation is not supported by this browser.');
      setStatus('unavailable');
      return;
    }
    if (!isSecureContext) {
      setError('GPS requires a secure connection (HTTPS).');
      setStatus('unavailable');
      return;
    }
    // Call getCurrentPosition immediately (before setState) so iOS Safari shows the permission
    // prompt — it must run in the same user-gesture stack. maximumAge: 0 forces a fresh request.
    const opts = {
      enableHighAccuracy: true,
      timeout: 20000,
      maximumAge: 0, // iOS: 0 ensures the system prompt is shown instead of returning cached position
    };
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setPosition({ latitude: pos.coords.latitude, longitude: pos.coords.longitude, accuracy: pos.coords.accuracy });
        setError(null);
        setStatus('allowed');
      },
      (err) => {
        setPosition(null);
        const message =
          err.code === 1 ? 'Location permission denied.' : err.code === 2 ? 'Location unavailable.' : err.message || 'Could not get location.';
        setError(message);
        setStatus(err.code === 1 ? 'denied' : 'error');
      },
      opts
    );
    setStatus('requesting');
    setError(null);
  }, [isSecureContext]);

  return { position, error, status, isSecureContext, requestLocation };
}
