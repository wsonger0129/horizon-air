import React from 'react';
import './DroneVideoPlaceholder.css';

/**
 * Placeholder for MJPEG/WebRTC drone stream. Replace <div> with <video> or
 * MJPEG img src when backend provides stream URL.
 */
export function DroneVideoPlaceholder() {
  return (
    <div className="drone-video" aria-label="Live drone camera feed">
      <div className="drone-video__placeholder">
        <span className="drone-video__icon" aria-hidden>📡</span>
        <p className="drone-video__label">Live Drone Feed</p>
        <p className="drone-video__hint">Stream placeholder — connect to drone for MJPEG/WebRTC</p>
      </div>
      <div className="drone-video__live-badge">LIVE</div>
    </div>
  );
}
