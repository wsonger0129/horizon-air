import React from 'react';
import './DirectionArrows.css';

/**
 * Placeholder direction indicator: arrow points toward drone/target.
 * bearing = direction to target in degrees (0 = N, 90 = E).
 * heading = current device heading. Arrow rotation = (bearing - heading).
 */
export function DirectionArrows({ bearing, heading }) {
  const rotation = ((bearing - (heading ?? 0) + 360) % 360);

  return (
    <div className="direction-arrows" aria-label="Direction to drone">
      <span className="direction-arrows__label">Point this way to drone</span>
      <div className="direction-arrows__wrap">
        <span
          className="direction-arrows__arrow"
          style={{ transform: `rotate(${rotation}deg)` }}
          aria-hidden
        >
          ▲
        </span>
      </div>
    </div>
  );
}
