import React from 'react';
import { getPiBaseUrl } from '../../config/pi';
import { usePiTelemetry } from '../../hooks/usePiTelemetry';
import { useConnectionStrength } from '../../hooks/useConnectionStrength';
import { DroneVideoPlaceholder } from './DroneVideoPlaceholder';
import { TelemetryOverlay } from './TelemetryOverlay';
import './LiveFeedTab.css';

export function LiveFeedTab() {
  const piBaseUrl = getPiBaseUrl();
  const { telemetry } = usePiTelemetry(piBaseUrl);
  const connection = useConnectionStrength(piBaseUrl);

  return (
    <section
      id="panel-feed"
      className="live-feed-tab"
      aria-label="Live drone feed"
    >
      <div className="live-feed-tab__video-wrap">
        <DroneVideoPlaceholder />
        <TelemetryOverlay telemetry={telemetry} connection={connection} />
      </div>
    </section>
  );
}
