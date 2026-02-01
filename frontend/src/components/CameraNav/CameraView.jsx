import React, { useRef, useEffect } from 'react';
import './CameraView.css';

export function CameraView({ stream, error, status, onStart, onStop }) {
  const videoRef = useRef(null);

  useEffect(() => {
    if (!videoRef.current || !stream) return;
    videoRef.current.srcObject = stream;
  }, [stream]);

  if (error) {
    const needsHttps = error.includes('secure connection') || error.includes('HTTPS');
    return (
      <div className="camera-view camera-view--error">
        <p className="camera-view__message">{error}</p>
        <p className="camera-view__hint">
          {needsHttps
            ? 'On iPhone: open this site over HTTPS (e.g. use ngrok: run "ngrok http 5173" on your laptop, then open the https:// URL in Safari). Or open http://localhost:5173 on your laptop only.'
            : 'Allow camera in Safari settings and try again.'}
        </p>
        <button type="button" className="camera-view__btn" onClick={onStart}>
          Try Again
        </button>
      </div>
    );
  }

  if (status === 'active' && stream) {
    return (
      <div className="camera-view camera-view--active">
        <video
          ref={videoRef}
          className="camera-view__video"
          autoPlay
          playsInline
          muted
          aria-label="Camera preview for navigation"
        />
        <button type="button" className="camera-view__btn camera-view__btn--stop" onClick={onStop}>
          Stop Camera
        </button>
      </div>
    );
  }

  return (
    <div className="camera-view camera-view--idle">
      <span className="camera-view__icon" aria-hidden>📷</span>
      <p className="camera-view__message">iPhone camera for GPS-based guidance</p>
      <p className="camera-view__hint">Enable camera to see your view and align with drone direction.</p>
      <button
        type="button"
        className="camera-view__btn"
        onClick={onStart}
        disabled={status === 'asking'}
      >
        {status === 'asking' ? 'Requesting…' : 'Start Camera'}
      </button>
    </div>
  );
}
