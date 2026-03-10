import React, { useState, useEffect } from 'react';
import { AppHeader } from './components/Layout/AppHeader';
import { TabBar } from './components/Layout/TabBar';
import { LiveFeedTab } from './components/LiveFeed/LiveFeedTab';
import { CameraNavTab } from './components/CameraNav/CameraNavTab';
import { ScenicAlertsTab } from './components/ScenicAlerts/ScenicAlertsTab';
import { useGeolocation } from './hooks/useGeolocation';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('feed');
  const geolocation = useGeolocation();

  // Request GPS as soon as the user enters the site (Live Feed is the first tab they see).
  useEffect(() => {
    geolocation.requestLocation();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps -- run once on mount

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
