import React, { useState } from 'react';
import { AppHeader } from './components/Layout/AppHeader';
import { TabBar } from './components/Layout/TabBar';
import { LiveFeedTab } from './components/LiveFeed/LiveFeedTab';
import { CameraNavTab } from './components/CameraNav/CameraNavTab';
import { ScenicAlertsTab } from './components/ScenicAlerts/ScenicAlertsTab';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('feed');

  return (
    <div className="app">
      <AppHeader />
      <main className="app__main" role="main">
        {activeTab === 'feed' && <LiveFeedTab />}
        {activeTab === 'camera' && <CameraNavTab />}
        {activeTab === 'alerts' && <ScenicAlertsTab />}
      </main>
      <TabBar activeTab={activeTab} onTabChange={setActiveTab} />
    </div>
  );
}
