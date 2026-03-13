import React from 'react';
import { AppHeader } from './components/Layout/AppHeader';
import { LiveFeedTab } from './components/LiveFeed/LiveFeedTab';
import { LocationPrompt } from './components/CameraNav/LocationPrompt';
import { useGeolocation } from './hooks/useGeolocation';
import './App.css';

export default function App() {
  const geolocation = useGeolocation();

  // Don't auto-request on load: it caused the prompt to disappear right after refresh on iPhone
  // (getCurrentPosition can resolve very quickly when permission was already granted). Request
  // only when the user taps "Enable GPS" so the prompt stays visible and the system dialog is
  // triggered by a user gesture.

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
