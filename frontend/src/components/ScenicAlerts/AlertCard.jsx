import React from 'react';
import './AlertCard.css';

function formatTimestamp(isoString) {
  const d = new Date(isoString);
  const now = new Date();
  const diffMs = now - d;
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} min ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours} h ago`;
  return d.toLocaleDateString();
}

export function AlertCard({ alert, onNavigate }) {
  const { thumbnail, description, timestamp, navigating } = alert;

  return (
    <article className="alert-card" aria-label={`Scenic alert: ${description}`}>
      <div className="alert-card__media">
        <img
          src={thumbnail}
          alt=""
          className="alert-card__thumb"
          loading="lazy"
        />
        <span className="alert-card__time">{formatTimestamp(timestamp)}</span>
      </div>
      <div className="alert-card__body">
        <p className="alert-card__description">{description}</p>
        <button
          type="button"
          className="alert-card__cta cta"
          onClick={onNavigate}
          disabled={navigating}
        >
          {navigating ? 'Navigating…' : 'Navigate to Location'}
        </button>
      </div>
    </article>
  );
}
