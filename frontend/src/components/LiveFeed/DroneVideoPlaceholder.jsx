import React, { useState } from 'react';
import { getPiBaseUrl } from '../../config/pi';
import './DroneVideoPlaceholder.css';

/**
 * Live MJPEG drone stream from Pi. Shows connecting/placeholder on error.
 */
export function DroneVideoPlaceholder() {
  const [status, setStatus] = useState('connecting'); // 'connecting' | 'playing' | 'error'
  const piBaseUrl = getPiBaseUrl();
  // FastAPI (Pi) uses /stream; legacy Flask uses /video_feed. Same-origin (Pi build) => /stream
  const videoFeedUrl = piBaseUrl && import.meta.env?.VITE_SERVE_FROM_PI === 'true'
    ? `${piBaseUrl}/stream`
    : `${piBaseUrl}/video_feed`;

  const showPlaceholder = status === 'connecting' || status === 'error';

  return (
    <div className="drone-video" aria-label="Live drone camera feed">
      {showPlaceholder && (
        <div className="drone-video__placeholder">
          <span className="drone-video__icon" aria-hidden>📡</span>
          <p className="drone-video__label">Live Drone Feed</p>
          <p className="drone-video__hint">
            {status === 'connecting'
              ? 'Connecting…'
              : 'Stream unavailable — check drone connection'}
          </p>
        </div>
      )}
      <img
        className="drone-video__stream"
        src={videoFeedUrl}
        alt="Live drone camera"
        style={{ display: showPlaceholder ? 'none' : 'block' }}
        onLoad={() => setStatus('playing')}
        onError={() => setStatus('error')}
      />
      <div className="drone-video__live-badge">LIVE</div>
    </div>
  );
}
