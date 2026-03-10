import React from 'react';
import { getPiBaseUrl } from '../../config/pi';
import { usePiTelemetry } from '../../hooks/usePiTelemetry';
import { useConnectionStrength } from '../../hooks/useConnectionStrength';
import { DroneVideoPlaceholder } from './DroneVideoPlaceholder';
import { TelemetryOverlay } from './TelemetryOverlay';
import { LocationPrompt } from '../CameraNav/LocationPrompt';
import './LiveFeedTab.css';

export function LiveFeedTab({ geolocation }) {
  const piBaseUrl = getPiBaseUrl();
  const { telemetry } = usePiTelemetry(piBaseUrl);
  const connection = useConnectionStrength(piBaseUrl);

  return (
    <section
      id="panel-feed"
      role="tabpanel"
      aria-labelledby="tab-feed"
      className="live-feed-tab"
    >
      <LocationPrompt
        isSecureContext={geolocation.isSecureContext}
        status={geolocation.status}
        error={geolocation.error}
        onRequest={geolocation.requestLocation}
      />
      <div className="live-feed-tab__video-wrap">
        <DroneVideoPlaceholder />
        <TelemetryOverlay telemetry={telemetry} connection={connection} />
      </div>
    </section>
  );
}
