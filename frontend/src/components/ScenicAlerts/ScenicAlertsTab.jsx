import React from 'react';
import { useMockScenicAlerts } from '../../hooks/useMockScenicAlerts';
import { AlertCard } from './AlertCard';
import './ScenicAlertsTab.css';

export function ScenicAlertsTab() {
  const { alerts, navigateToLocation } = useMockScenicAlerts();

  return (
    <section
      id="panel-alerts"
      role="tabpanel"
      aria-labelledby="tab-alerts"
      className="scenic-alerts-tab"
    >
      <h2 className="scenic-alerts-tab__title">Scenic Detection Alerts</h2>
      <p className="scenic-alerts-tab__subtitle">
        Areas detected by the drone. Tap to navigate.
      </p>
      <ul className="scenic-alerts-tab__list" aria-label="Scenic alerts">
        {alerts.map((alert) => (
          <li key={alert.id}>
            <AlertCard alert={alert} onNavigate={() => navigateToLocation(alert.id)} />
          </li>
        ))}
      </ul>
    </section>
  );
}
