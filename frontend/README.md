# HorizonAir Ground Station (Web)

Mobile-first React ground-station UI for the HorizonAir drone system. Optimized for iPhone Safari.

## Run locally

```bash
npm install
npm run dev
```

Open the URL shown (e.g. `http://localhost:5173`) in Safari on your iPhone or in a desktop browser. For camera and compass on iOS, use HTTPS or a tunnel (e.g. ngrok).

## Project structure

- `src/components/Layout/` — App header, tab bar
- `src/components/LiveFeed/` — Live drone feed placeholder, telemetry overlay
- `src/components/CameraNav/` — iPhone camera view, compass, distance, direction arrows
- `src/components/ScenicAlerts/` — Scenic detection alert cards and “Navigate to Location” CTA
- `src/api/mockData.js` — Mock telemetry and scenic alerts (replace with REST/WebSocket)
- `src/hooks/` — `useMockTelemetry`, `useMockScenicAlerts`, `useCamera`

## Backend integration

- Telemetry: replace `useMockTelemetry` with a WebSocket or polling hook that consumes your Python backend.
- Scenic alerts: replace `useMockScenicAlerts` and `mockScenicAlerts` with REST/WebSocket.
- Live feed: replace `DroneVideoPlaceholder` with a `<video>` or MJPEG `<img>` pointed at your stream URL.
