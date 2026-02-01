# HorizonAir Ground Station (Web)

Mobile-first React ground-station UI for the HorizonAir drone system. Optimized for iPhone Safari.

## Run locally

```bash
npm install
npm run dev
```

Open the URL shown (e.g. `http://localhost:5173`) in a desktop browser. To use the **camera** or **compass** on an iPhone, the app must be loaded over HTTPS — use ngrok (see below).

### Testing on iPhone with ngrok (HTTPS)

Safari only allows camera and device orientation over HTTPS or localhost. To test on your phone over Wi‑Fi or cellular, expose the dev server via ngrok:

1. **Install ngrok**
   - macOS (Homebrew): `brew install ngrok/ngrok/ngrok`
   - Or download from [ngrok.com/download](https://ngrok.com/download) and add `ngrok` to your PATH.
   - Optional: sign up at [ngrok.com](https://ngrok.com) and run `ngrok config add-authtoken YOUR_TOKEN` to avoid free-tier limits.

2. **Start the frontend** (terminal 1)
   ```bash
   npm run dev
   ```
   Leave this running.

3. **Start ngrok** (terminal 2)
   ```bash
   ngrok http 5173
   ```
   Ngrok will print a line like:
   ```
   Forwarding   https://xxxx.ngrok-free.app -> http://localhost:5173
   ```

4. **Open on your iPhone**
   - In Safari, go to the **https** URL ngrok showed (e.g. `https://xxxx.ngrok-free.app`).
   - On first load, you may see an ngrok “Visit Site” screen — tap it to continue.
   - The Camera tab will work over this HTTPS URL.

5. **When done**
   - Stop ngrok with **Ctrl+C** in the ngrok terminal.
   - Stop Vite with **Ctrl+C** in the Vite terminal.

The project’s `vite.config.js` has `server.allowedHosts: true` so Vite accepts requests when the host is your ngrok domain.

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
