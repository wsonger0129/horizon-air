import React, { useEffect } from 'react';
import { AppHeader } from './components/Layout/AppHeader';
import { LiveFeedTab } from './components/LiveFeed/LiveFeedTab';
import { LocationPrompt } from './components/CameraNav/LocationPrompt';
import { useGeolocation } from './hooks/useGeolocation';
import { getPiBaseUrl } from './config/pi';
import './App.css';

export default function App() {
  const geolocation = useGeolocation();

  // Don't auto-request on load: it caused the prompt to disappear right after refresh on iPhone
  // (getCurrentPosition can resolve very quickly when permission was already granted). Request
  // only when the user taps "Enable GPS" so the prompt stays visible and the system dialog is
  // triggered by a user gesture.

  // When we have GPS, send position to backend for droneMain (proximity / follow). Post once and every 1s.
  useEffect(() => {
    const position = geolocation.position;
    if (!position) return;

    const baseUrl = getPiBaseUrl();
    const post = () => {
      fetch(`${baseUrl}/drone/phone_position`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lat: position.latitude, lon: position.longitude }),
      }).catch(() => {});
    };

    post();
    const interval = setInterval(post, 1000);
    return () => clearInterval(interval);
  }, [geolocation.position]);

  return (
    <div className="app">
      <AppHeader />
      <main className="app__main" role="main">
        <div className="app__feed-wrap">
          <LocationPrompt
            isSecureContext={geolocation.isSecureContext}
            status={geolocation.status}
            error={geolocation.error}
            onRequest={geolocation.requestLocation}
          />
          <LiveFeedTab />
        </div>
      </main>
    </div>
  );
}
