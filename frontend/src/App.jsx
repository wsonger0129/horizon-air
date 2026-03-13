import React, { useState, useEffect } from 'react';
import { AppHeader } from './components/Layout/AppHeader';
import { TabBar } from './components/Layout/TabBar';
import { LiveFeedTab } from './components/LiveFeed/LiveFeedTab';
import { CameraNavTab } from './components/CameraNav/CameraNavTab';
import { ScenicAlertsTab } from './components/ScenicAlerts/ScenicAlertsTab';
import { LocationPrompt } from './components/CameraNav/LocationPrompt';
import { useGeolocation } from './hooks/useGeolocation';
import { getPiBaseUrl } from './config/pi';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('feed');
  const geolocation = useGeolocation();
  const piBaseUrl = getPiBaseUrl();

  // Request GPS as soon as the user enters the site (Live Feed is the default tab).
  useEffect(() => {
    geolocation.requestLocation();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Post phone GPS to backend for droneMain proximity (all tabs).
  useEffect(() => {
    if (!geolocation.position || !piBaseUrl) return;
    const send = () => {
      if (!geolocation.position) return;
      fetch(`${piBaseUrl}/drone/phone_position`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lat: geolocation.position.latitude,
          lon: geolocation.position.longitude,
        }),
      }).catch(() => {});
    };
    send();
    const interval = setInterval(send, 3000);
    return () => clearInterval(interval);
  }, [geolocation.position, piBaseUrl]);

  return (
    <div className="app">
      <AppHeader />
      <TabBar activeTab={activeTab} onTabChange={setActiveTab} />
      <main className="app__main" role="main">
        {/* GPS prompt only on Live Feed tab — requested on enter in useEffect above */}
        {activeTab === 'feed' && (
          <div className="app__feed-wrap">
            <LocationPrompt
              isSecureContext={geolocation.isSecureContext}
              status={geolocation.status}
              error={geolocation.error}
              onRequest={geolocation.requestLocation}
            />
            <LiveFeedTab />
          </div>
        )}
        {activeTab === 'camera' && <CameraNavTab position={geolocation.position} />}
        {activeTab === 'alerts' && <ScenicAlertsTab />}
      </main>
    </div>
  );
}
