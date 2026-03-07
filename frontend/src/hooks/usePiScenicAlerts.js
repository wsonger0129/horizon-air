import { useState, useEffect, useCallback } from 'react';
import { mockScenicAlerts } from '../api/mockData';

const POLL_MS = 5000;

function normalizeAlert(a) {
  return {
    id: String(a.id),
    thumbnail: a.thumbnail || '',
    description: a.description || '',
    timestamp: typeof a.timestamp === 'number' ? new Date(a.timestamp).toISOString() : a.timestamp,
    location: a.location || { lat: 0, lng: 0 },
    confidence: a.confidence ?? 0,
    navigating: a.navigating ?? false,
  };
}

/**
 * Fetches scenic alerts from Pi. Falls back to mock on error or while loading.
 */
export function usePiScenicAlerts(piBaseUrl) {
  const [alerts, setAlerts] = useState(mockScenicAlerts);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const navigateToLocation = useCallback((alertId) => {
    setAlerts((prev) =>
      prev.map((a) => (a.id === alertId ? { ...a, navigating: true } : a))
    );
    console.log('Navigate to location for alert:', alertId);
  }, []);

  useEffect(() => {
    if (!piBaseUrl) {
      setAlerts(mockScenicAlerts);
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;

    const fetchScenic = async () => {
      try {
        const res = await fetch(`${piBaseUrl}/api/scenic`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (cancelled) return;
        setAlerts(Array.isArray(data) ? data.map(normalizeAlert) : mockScenicAlerts);
        setError(null);
      } catch (e) {
        if (!cancelled) {
          setError(e);
          setAlerts(mockScenicAlerts);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    setLoading(true);
    fetchScenic();
    const interval = setInterval(fetchScenic, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [piBaseUrl]);

  return { alerts, navigateToLocation, loading, error };
}
