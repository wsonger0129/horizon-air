import React from 'react';
import { useMockTelemetry } from '../../hooks/useMockTelemetry';
import { DroneVideoPlaceholder } from './DroneVideoPlaceholder';
import { TelemetryOverlay } from './TelemetryOverlay';
import './LiveFeedTab.css';

export function LiveFeedTab() {
  const telemetry = useMockTelemetry();

  return (
    <section
      id="panel-feed"
      role="tabpanel"
      aria-labelledby="tab-feed"
      className="live-feed-tab"
    >
      <div className="live-feed-tab__video-wrap">
        <DroneVideoPlaceholder />
        <TelemetryOverlay telemetry={telemetry} />
      </div>
    </section>
  );
}
