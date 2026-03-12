import React, { useState, useEffect } from 'react';
import { AppHeader } from './components/Layout/AppHeader';
import { TabBar } from './components/Layout/TabBar';
import { LiveFeedTab } from './components/LiveFeed/LiveFeedTab';
import { CameraNavTab } from './components/CameraNav/CameraNavTab';
import { ScenicAlertsTab } from './components/ScenicAlerts/ScenicAlertsTab';
import { useGeolocation } from './hooks/useGeolocation';
import { getPiBaseUrl } from './config/pi';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('feed');
  const geolocation = useGeolocation();
  const piBaseUrl = getPiBaseUrl();

  // Request GPS on mount
  useEffect(() => {
    geolocation.requestLocation();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Post phone GPS to /api/location every 1s regardless of active tab
  useEffect(() => {
    if (!geolocation.position || !piBaseUrl) return;

    const send = () => {
      if (!geolocation.position) return;
      fetch(`${piBaseUrl}/api/location`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lat: geolocation.position.latitude,
          lon: geolocation.position.longitude,
        }),
      }).catch(() => {});
    };

    send();
    const interval = setInterval(send, 1000);
    return () => clearInterval(interval);
  }, [geolocation.position, piBaseUrl]);

  return (
    <div className="app">
      <AppHeader />
      <TabBar activeTab={activeTab} onTabChange={setActiveTab} />
      <main className="app__main" role="main">
        {activeTab === 'feed' && <LiveFeedTab geolocation={geolocation} />}
        {activeTab === 'camera' && <CameraNavTab position={geolocation.position} />}
        {activeTab === 'alerts' && <ScenicAlertsTab />}
      </main>
    </div>
  );
}
