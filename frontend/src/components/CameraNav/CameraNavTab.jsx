import React, { useState, useEffect } from 'react';
import { useCamera } from '../../hooks/useCamera';
import { useGeolocation } from '../../hooks/useGeolocation';
import { mockNavigationTarget } from '../../api/mockData';
import { CameraView } from './CameraView';
import { CompassHeading } from './CompassHeading';
import { DirectionArrows } from './DirectionArrows';
import { DistanceDisplay } from './DistanceDisplay';
import { LocationPrompt } from './LocationPrompt';
import './CameraNavTab.css';

export function CameraNavTab() {
  const { stream, error, status, startCamera, stopCamera } = useCamera();
  const { position, error: locationError, status: locationStatus, isSecureContext, requestLocation } = useGeolocation();
  const [heading, setHeading] = useState(null);
  const [headingError, setHeadingError] = useState(null);
  const nav = mockNavigationTarget;

  useEffect(() => {
    if (!('DeviceOrientationEvent' in window)) {
      setHeadingError('Compass not supported');
      return;
    }
    const onOrientation = (e) => {
      if (e.alpha != null) setHeading(e.alpha);
    };
    const permission = typeof DeviceOrientationEvent?.requestPermission === 'function';
    if (permission) {
      DeviceOrientationEvent.requestPermission()
        .then((p) => (p === 'granted' ? window.addEventListener('deviceorientation', onOrientation) : setHeadingError('Permission denied')))
        .catch(() => setHeadingError('Compass unavailable'));
    } else {
      window.addEventListener('deviceorientation', onOrientation);
    }
    return () => window.removeEventListener('deviceorientation', onOrientation);
  }, []);

  return (
    <section
      id="panel-camera"
      role="tabpanel"
      aria-labelledby="tab-camera"
      className="camera-nav-tab"
    >
      <LocationPrompt
        isSecureContext={isSecureContext}
        status={locationStatus}
        error={locationError}
        onRequest={requestLocation}
      />
      <div className="camera-nav-tab__camera">
        <CameraView stream={stream} error={error} status={status} onStart={startCamera} onStop={stopCamera} />
      </div>
      <div className="camera-nav-tab__nav">
        <h2 className="camera-nav-tab__section-title">Navigation to Drone</h2>
        <CompassHeading heading={heading ?? nav.heading} error={headingError} />
        <DistanceDisplay distanceMeters={nav.distanceMeters} />
        <DirectionArrows bearing={nav.bearing} heading={heading ?? nav.heading} />
      </div>
    </section>
  );
}
