import { useState, useEffect } from 'react';
import { mockTelemetry } from '../api/mockData';

const POLL_MS = 2000;

/**
 * Fetches telemetry from Pi. Falls back to mock on error or while loading.
 */
export function usePiTelemetry(piBaseUrl) {
  const [telemetry, setTelemetry] = useState(mockTelemetry);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!piBaseUrl) {
      setTelemetry(mockTelemetry);
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;

    const fetchTelemetry = async () => {
      try {
        const res = await fetch(`${piBaseUrl}/api/telemetry`);
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();
        if (cancelled) return;
        setTelemetry({
          altitude: data.altitude ?? mockTelemetry.altitude,
          altitudeUnit: data.altitudeUnit ?? mockTelemetry.altitudeUnit,
          batteryPercent: data.batteryPercent ?? mockTelemetry.batteryPercent,
          signalStrength: data.signalStrength ?? mockTelemetry.signalStrength,
          signalMax: data.signalMax ?? mockTelemetry.signalMax,
          latitude: data.latitude ?? mockTelemetry.latitude,
          longitude: data.longitude ?? mockTelemetry.longitude,
          heading: data.heading ?? mockTelemetry.heading,
          speed: data.speed ?? mockTelemetry.speed,
        });
        setError(null);
      } catch (e) {
        if (!cancelled) {
          setError(e);
          setTelemetry(mockTelemetry);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    setLoading(true);
    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [piBaseUrl]);

  return { telemetry, loading, error };
}
