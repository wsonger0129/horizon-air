import React from 'react';
import './LocationPrompt.css';

/**
 * Prompts the user to allow GPS so the app can use location for navigation.
 * Safari only shows the system location dialog when the page is HTTPS (secure context).
 */
export function LocationPrompt({ isSecureContext, status, error, onRequest }) {
  if (status === 'allowed') return null;

  if (!isSecureContext) {
    return (
      <div className="location-prompt location-prompt--https" role="status">
        <span className="location-prompt__icon" aria-hidden>🔒</span>
        <p className="location-prompt__title">GPS requires HTTPS</p>
        <p className="location-prompt__text">
          To use your location for navigation, open this site over HTTPS (e.g.{' '}
          <strong>https://&lt;Pi-IP&gt;:8443</strong>). Accept the certificate warning in Safari, then return to this tab and enable GPS.
        </p>
      </div>
    );
  }

  if (status === 'denied' || (status === 'error' && error?.includes('denied'))) {
    return (
      <div className="location-prompt location-prompt--denied" role="status">
        <span className="location-prompt__icon" aria-hidden>📍</span>
        <p className="location-prompt__title">Location denied</p>
        <p className="location-prompt__text">You can allow location in Safari: Settings → Safari → Location → this website.</p>
        <button type="button" className="location-prompt__btn" onClick={onRequest}>
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className="location-prompt" role="status">
      <span className="location-prompt__icon" aria-hidden>📍</span>
      <p className="location-prompt__title">Allow location for GPS navigation</p>
      <p className="location-prompt__text">This site uses your location to show distance and direction to the drone. Safari will ask for permission.</p>
      <button
        type="button"
        className="location-prompt__btn"
        onClick={onRequest}
        disabled={status === 'requesting'}
      >
        {status === 'requesting' ? 'Requesting…' : 'Enable GPS'}
      </button>
      {error && status !== 'requesting' && <p className="location-prompt__error">{error}</p>}
    </div>
  );
}
