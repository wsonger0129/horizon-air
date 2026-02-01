import { useState, useEffect } from 'react';
import { mockTelemetry } from '../api/mockData';

/**
 * Simulates live telemetry from backend. Replace with WebSocket subscription.
 */
export function useMockTelemetry() {
  const [telemetry, setTelemetry] = useState(mockTelemetry);

  useEffect(() => {
    const interval = setInterval(() => {
      setTelemetry((prev) => ({
        ...prev,
        altitude: Math.max(0, prev.altitude + (Math.random() - 0.5) * 4),
        batteryPercent: Math.max(0, Math.min(100, prev.batteryPercent - Math.random() * 0.1)),
        signalStrength: Math.max(1, Math.min(5, prev.signalStrength + (Math.random() > 0.95 ? 1 : 0) * (Math.random() > 0.5 ? 1 : -1))),
        heading: (prev.heading + (Math.random() - 0.5) * 2 + 360) % 360,
      }));
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return telemetry;
}
