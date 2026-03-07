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
      role="tabpanel"
      aria-labelledby="tab-feed"
      className="live-feed-tab"
    >
      <div className="live-feed-tab__video-wrap">
        <DroneVideoPlaceholder />
        <TelemetryOverlay telemetry={telemetry} />
        <div
          className="live-feed-tab__connection"
          data-quality={connection.quality}
          aria-live="polite"
          aria-label={`Connection ${connection.quality}${connection.rttMs != null ? `, ${connection.rttMs} ms round-trip` : ''}`}
        >
          {connection.quality}
          {connection.rttMs != null && ` · ${connection.rttMs} ms`}
        </div>
      </div>
    </section>
  );
}
