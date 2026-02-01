import React from 'react';
import './DistanceDisplay.css';

function formatDistance(meters) {
  if (meters >= 1000) return `${(meters / 1000).toFixed(1)} km`;
  return `${Math.round(meters)} m`;
}

export function DistanceDisplay({ distanceMeters }) {
  return (
    <div className="distance" aria-label={`Distance to target ${formatDistance(distanceMeters)}`}>
      <span className="distance__label">Distance to drone</span>
      <span className="distance__value">{formatDistance(distanceMeters)}</span>
    </div>
  );
}
