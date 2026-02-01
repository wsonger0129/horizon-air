import React from 'react';
import './TelemetryOverlay.css';

export function TelemetryOverlay({ telemetry }) {
  const { altitude, altitudeUnit, batteryPercent, signalStrength, signalMax } = telemetry;
  const signalBars = Array.from({ length: signalMax }, (_, i) => i < signalStrength);

  return (
    <div className="telemetry" aria-label="Drone telemetry">
      <div className="telemetry__item">
        <span className="telemetry__label">ALT</span>
        <span className="telemetry__value">
          {Math.round(altitude)} {altitudeUnit}
        </span>
      </div>
      <div className="telemetry__item">
        <span className="telemetry__label">BAT</span>
        <span className={`telemetry__value telemetry__value--${batteryPercent > 20 ? 'ok' : 'low'}`}>
          {Math.round(batteryPercent)}%
        </span>
      </div>
      <div className="telemetry__item telemetry__item--signal">
        <span className="telemetry__label">SIG</span>
        <span className="telemetry__signal" aria-label={`Signal strength ${signalStrength} of ${signalMax}`}>
          {signalBars.map((filled, i) => (
            <span
              key={i}
              className={`telemetry__bar ${filled ? 'telemetry__bar--on' : ''}`}
              aria-hidden
            />
          ))}
        </span>
      </div>
    </div>
  );
}
