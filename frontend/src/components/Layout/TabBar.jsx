import React from 'react';
import './TabBar.css';

const TABS = [
  { id: 'feed', label: 'Live Feed', icon: '📡' },
  { id: 'camera', label: 'Camera', icon: '📷' },
  { id: 'alerts', label: 'Alerts', icon: '🔔' },
];

export function TabBar({ activeTab, onTabChange }) {
  return (
    <nav className="tab-bar" role="tablist" aria-label="Ground station sections">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          aria-selected={activeTab === tab.id}
          aria-controls={`panel-${tab.id}`}
          id={`tab-${tab.id}`}
          className={`tab-bar__item ${activeTab === tab.id ? 'tab-bar__item--active' : ''}`}
          onClick={() => onTabChange(tab.id)}
        >
          <span className="tab-bar__icon" aria-hidden>{tab.icon}</span>
          <span className="tab-bar__label">{tab.label}</span>
        </button>
      ))}
    </nav>
  );
}
