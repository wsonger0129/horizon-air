import React from 'react';
import './CompassHeading.css';

function formatHeading(deg) {
  if (deg == null) return '—';
  const d = Math.round(deg) % 360;
  const labels = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
  const i = Math.round(d / 45) % 8;
  return `${labels[i]} ${d}°`;
}

export function CompassHeading({ heading, error }) {
  if (error) {
    return (
      <div className="compass" aria-label="Compass heading unavailable">
        <span className="compass__label">Heading</span>
        <span className="compass__value compass__value--error">{error}</span>
      </div>
    );
  }

  return (
    <div className="compass" aria-label={`Compass heading ${formatHeading(heading)}`}>
      <span className="compass__label">Heading</span>
      <span className="compass__value">{formatHeading(heading)}</span>
      <span
        className="compass__needle"
        style={{ transform: `rotate(${heading ?? 0}deg)` }}
        aria-hidden
      />
    </div>
  );
}
