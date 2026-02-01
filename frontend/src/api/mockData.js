/**
 * Mock data for ground station UI. Replace with REST/WebSocket when backend is ready.
 */

export const mockTelemetry = {
  altitude: 42,
  altitudeUnit: 'm',
  batteryPercent: 78,
  signalStrength: 4,
  signalMax: 5,
  latitude: 33.6461,
  longitude: -117.8427,
  heading: 180,
  speed: 0,
};

export const mockScenicAlerts = [
  {
    id: '1',
    thumbnail: 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400&h=300&fit=crop',
    description: 'Wide mountain vista detected — clear view to the east.',
    timestamp: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
    location: { lat: 33.647, lng: -117.843 },
    confidence: 0.92,
  },
  {
    id: '2',
    thumbnail: 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=400&h=300&fit=crop',
    description: 'Scenic clearing with lake view ahead.',
    timestamp: new Date(Date.now() - 8 * 60 * 1000).toISOString(),
    location: { lat: 33.648, lng: -117.844 },
    confidence: 0.88,
  },
  {
    id: '3',
    thumbnail: 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=400&h=300&fit=crop',
    description: 'Ridge viewpoint — ideal for sunset.',
    timestamp: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
    location: { lat: 33.645, lng: -117.841 },
    confidence: 0.85,
  },
];

export const mockNavigationTarget = {
  heading: 45,
  distanceMeters: 120,
  bearing: 48,
};
