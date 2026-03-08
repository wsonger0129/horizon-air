import React from 'react';
import './TelemetryOverlay.css';

const SIGNAL_BARS_MAX = 3;
/** Bars to show from connection quality (ping). */
function signalBarsFromConnection(connection) {
  if (!connection) return null;
  const filled =
    connection.quality === 'good' ? 3
    : connection.quality === 'degraded' ? 2
    : 0; /* lost */
  return Array.from({ length: SIGNAL_BARS_MAX }, (_, i) => i < filled);
}

export function TelemetryOverlay({ telemetry, connection }) {
  const { altitude, altitudeUnit, batteryPercent, signalStrength, signalMax } = telemetry;
  const barsFromPing = signalBarsFromConnection(connection);
  const signalBars =
    barsFromPing != null
      ? barsFromPing
      : (() => {
          const scale = signalMax > 0 ? signalStrength / signalMax : 0;
          const filled = Math.min(SIGNAL_BARS_MAX, Math.max(0, Math.round(scale * SIGNAL_BARS_MAX)));
          return Array.from({ length: SIGNAL_BARS_MAX }, (_, i) => i < filled);
        })();

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
      {connection && (
        <div
          className="telemetry__item telemetry__item--connection"
          data-quality={connection.quality}
          aria-label={`Connection ${connection.quality}${connection.rttMs != null ? `, ${connection.rttMs} ms round-trip` : ''}`}
        >
          <span className="telemetry__label">PING</span>
          <span className="telemetry__connection-value">
            {connection.quality}
            {connection.rttMs != null && ` · ${connection.rttMs} ms`}
          </span>
        </div>
      )}
      <div className="telemetry__item telemetry__item--signal">
        <span className="telemetry__label">SIG</span>
        <span
          className="telemetry__signal"
          aria-label={
            connection
              ? `Link ${connection.quality}${connection.rttMs != null ? `, ${connection.rttMs} ms` : ''}`
              : `Signal ${signalMax > 0 ? Math.min(3, Math.round((signalStrength / signalMax) * 3)) : 0} of 3`
          }
        >
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
