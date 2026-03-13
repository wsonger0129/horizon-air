import React, { useEffect } from 'react';
import { AppHeader } from './components/Layout/AppHeader';
import { LiveFeedTab } from './components/LiveFeed/LiveFeedTab';
import { LocationPrompt } from './components/CameraNav/LocationPrompt';
import { useGeolocation } from './hooks/useGeolocation';
import './App.css';

export default function App() {
  const geolocation = useGeolocation();

  // Request GPS as soon as the user enters the site.
  useEffect(() => {
    geolocation.requestLocation();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

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
