import { useState, useCallback } from 'react';
import { mockScenicAlerts } from '../api/mockData';

/**
 * Mock scenic alerts. Replace with REST/WebSocket when backend is ready.
 */
export function useMockScenicAlerts() {
  const [alerts, setAlerts] = useState(mockScenicAlerts);

  const navigateToLocation = useCallback((alertId) => {
    // Stub: would call backend or open map with coordinates
    console.log('Navigate to location for alert:', alertId);
    setAlerts((prev) => prev.map((a) => (a.id === alertId ? { ...a, navigating: true } : a)));
  }, []);

  return { alerts, navigateToLocation };
}
