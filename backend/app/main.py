"""
HorizonAir — runs entirely on the Raspberry Pi Zero 2W.

Video pipeline (no ffmpeg — saves ~50MB RAM + significant CPU):
  rpicam-vid --codec mjpeg → stdout → FastAPI /stream endpoint
  IMX500 handles object detection on-chip.
  Pi CPU is barely involved in video encoding.

Serves:
  http://192.168.50.1:8000          → React app (or :8443 with HTTPS via run_https.sh)
  /stream, /video_feed              → MJPEG video stream
  /drone/*, /api/*                  → REST API

Run:
  HTTP:  uvicorn app.main:app --host 0.0.0.0 --port 8000
  HTTPS: ./run_https.sh  (for Safari GPS/camera/compass; use https://<Pi-IP>:8443)
"""

from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import threading
import time
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Repo layout: horizon-air/frontend/dist (build output). From backend/app/main.py -> ../.. = repo root.
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")


# -----------------------------------------------------------------------
# SHARED DRONE STATE
# -----------------------------------------------------------------------

class DroneStateStore:
    def __init__(self):
        self.pos_north       = 0.0
        self.pos_east        = 0.0
        self.altitude        = 0.0
        self.wp_north        = None
        self.wp_east         = None
        self.state           = "IDLE"
        self.armed           = False
        self.avoiding        = False
        self.rc_override     = False
        self.rssi            = None
        self.lidar           = None
        self.detections      = []
        self.pending_command = None
        self.last_update     = time.time()
        # For droneMain proximity: phone GPS (from web app), drone GPS (from FC), RTT (from heartbeat)
        self.phone_lat       = None
        self.phone_lon       = None
        self.phone_gps_update = None
        self.drone_lat       = None
        self.drone_lon       = None
        self.rtt_ms          = None

    def to_dict(self):
        return {
            "pos_north":        self.pos_north,
            "pos_east":         self.pos_east,
            "altitude":         self.altitude,
            "wp_north":         self.wp_north,
            "wp_east":          self.wp_east,
            "state":            self.state,
            "armed":            self.armed,
            "avoiding":         self.avoiding,
            "rc_override":      self.rc_override,
            "rssi":             self.rssi,
            "lidar":            self.lidar,
            "detections":       self.detections,
            "pending_command":  self.pending_command,
            "last_update":      self.last_update,
            "phone_lat":        self.phone_lat,
            "phone_lon":        self.phone_lon,
            "phone_gps_update": self.phone_gps_update,
            "drone_lat":        self.drone_lat,
            "drone_lon":       self.drone_lon,
            "rtt_ms":          self.rtt_ms,
        }

state_store = DroneStateStore()


# -----------------------------------------------------------------------
# CAMERA STREAM
# Uses native MJPEG output from rpicam-vid — no ffmpeg needed.
# The IMX500 chip handles object detection entirely on-chip.
# Pi CPU usage for video: near zero.
# -----------------------------------------------------------------------

class CameraStream:
    """
    Reads native MJPEG from rpicam-vid stdout.
    Each JPEG frame is delimited by SOI (FFD8) and EOI (FFD9) markers.
    threading.Event wakes up all viewers the instant a new frame arrives.
    """

    def __init__(self):
        self._frame     = None
        self._lock      = threading.Lock()
        self._new_frame = threading.Event()
        self._started   = False

    def start(self):
        if self._started:
            return
        self._started = True
        t = threading.Thread(target=self._capture_loop, daemon=True)
        t.start()
        print("[STREAM] Camera thread started (native MJPEG, no ffmpeg).")

    def get_frame(self):
        with self._lock:
            return self._frame

    def wait_for_frame(self, timeout=0.5):
        return self._new_frame.wait(timeout=timeout)

    def _capture_loop(self):
        """
        Runs rpicam-vid in MJPEG mode with IMX500 object detection.
        Parses the raw MJPEG bytestream into individual JPEG frames.
        Restarts automatically if the camera process dies.
        """
        cmd = [
            "rpicam-vid",
            "-t", "0",                  # run forever
            "-n",                       # no preview window
            "--codec", "mjpeg",         # native MJPEG — no ffmpeg needed
            "--width",  "320",          # 320x240 keeps CPU load low on Zero 2W
            "--height", "240",          # increase to 640x360 if Pi 4 is used
            "--framerate", "15",        # 15fps is smooth and light on resources
            "--bitrate", "2000000",     # 2Mbps is plenty for 320x240 MJPEG
            "--post-process-file",
            "/usr/share/rpi-camera-assets/imx500_mobilenet_ssd.json",
            "-o", "-",                  # pipe to stdout
        ]

        while True:
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    bufsize=0               # unbuffered — critical for low latency
                )
                print("[STREAM] rpicam-vid running.")

                buf = b""
                while True:
                    chunk = proc.stdout.read(4096)
                    if not chunk:
                        print("[STREAM] rpicam-vid ended unexpectedly.")
                        break

                    buf += chunk

                    # Extract all complete JPEG frames from the buffer
                    while True:
                        start = buf.find(b"\xff\xd8")   # JPEG SOI marker
                        end   = buf.find(b"\xff\xd9")   # JPEG EOI marker

                        if start == -1 or end == -1 or end <= start:
                            break   # no complete frame yet, wait for more data

                        frame = buf[start : end + 2]
                        buf   = buf[end + 2:]           # keep remainder

                        with self._lock:
                            self._frame = frame

                        # Instantly wake all waiting stream viewers
                        self._new_frame.set()
                        self._new_frame.clear()

                proc.wait()

            except Exception as e:
                print(f"[STREAM] Error: {e}")

            print("[STREAM] Restarting camera in 2s...")
            time.sleep(2)


camera_stream = CameraStream()


def generate_mjpeg():
    """
    Generator for each connected viewer.
    Blocks on wait_for_frame() until the camera thread signals a new frame,
    then immediately yields it. No polling, no sleep() delay.
    """
    while True:
        if camera_stream.wait_for_frame(timeout=0.5):
            frame = camera_stream.get_frame()
            if frame:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" +
                    frame +
                    b"\r\n"
                )


# -----------------------------------------------------------------------
# REQUEST MODELS
# -----------------------------------------------------------------------

class WaypointRequest(BaseModel):
    north_m: float
    east_m:  float

class CommandRequest(BaseModel):
    command: str

class HeartbeatRequest(BaseModel):
    ts: float
    rtt_ms: Optional[float] = None  # optional; stored for droneMain proximity fallback


class PhonePositionRequest(BaseModel):
    lat: float
    lon: float


# -----------------------------------------------------------------------
# FREE CAMERA BEFORE USE
# -----------------------------------------------------------------------

def _free_camera():
    """
    Kill any process holding the camera so rpicam-vid can open it.
    Run before starting the stream to avoid 'device or resource busy'.
    """
    for pattern in ("rpicam-vid", "rpicam-hello", "rpicam-still", "libcamera"):
        try:
            subprocess.run(
                ["pkill", "-f", pattern],
                capture_output=True,
                timeout=2,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            pass
    time.sleep(0.5)  # allow device to be released


# -----------------------------------------------------------------------
# STARTUP
# -----------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    _free_camera()
    camera_stream.start()
    print("[SERVER] HorizonAir running at http://192.168.50.1:8000")
    print("[SERVER] Open this URL on any device on the HorizonAir hotspot.")


# -----------------------------------------------------------------------
# API ROUTES
# -----------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/drone/state")
def get_state():
    return state_store.to_dict()


@app.get("/drone/waypoint")
def get_waypoint():
    if state_store.wp_north is None:
        return {"waypoint": None}
    return {"waypoint": {
        "north_m": state_store.wp_north,
        "east_m":  state_store.wp_east
    }}


@app.post("/drone/waypoint")
def set_waypoint(req: WaypointRequest):
    state_store.wp_north = req.north_m
    state_store.wp_east  = req.east_m
    return {"status": "waypoint set", "north_m": req.north_m, "east_m": req.east_m}


@app.delete("/drone/waypoint")
def clear_waypoint():
    state_store.wp_north = None
    state_store.wp_east  = None
    return {"status": "waypoint cleared"}


@app.post("/drone/command")
def send_command(req: CommandRequest):
    valid = {"arm", "takeoff", "land", "abort"}
    if req.command not in valid:
        raise HTTPException(status_code=400, detail=f"Valid commands: {valid}")
    state_store.pending_command = req.command
    return {"status": "command queued", "command": req.command}


@app.post("/heartbeat")
def heartbeat(req: HeartbeatRequest):
    """Keeps WiFi radio active; optional rtt_ms is stored for droneMain proximity fallback."""
    if req.rtt_ms is not None:
        state_store.rtt_ms = req.rtt_ms
    return {"ts": time.time()}


@app.post("/drone/phone_position")
def set_phone_position(req: PhonePositionRequest):
    """Store phone GPS from web app for droneMain proximity (GPS-based follow)."""
    state_store.phone_lat = req.lat
    state_store.phone_lon = req.lon
    state_store.phone_gps_update = time.time()
    return {"status": "ok", "lat": req.lat, "lon": req.lon}


@app.get("/stream")
def video_stream():
    """
    MJPEG stream with IMX500 object detection overlays.

    Embed in React with a simple relative URL:
        <img src="/stream" alt="drone feed" />

    Works on any device connected to HorizonAir hotspot.
    No ffmpeg, no specific IP, no extra setup.
    """
    return StreamingResponse(
        generate_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma":        "no-cache",
            "Age":           "0",
        }
    )


@app.get("/video_feed")
def video_feed_alias():
    """Alias for /stream so frontend built for legacy Flask (aiPiCam) works when served from Pi."""
    return video_stream()


# -----------------------------------------------------------------------
# COMPATIBILITY ROUTES — frontend expects these when talking to Pi
# -----------------------------------------------------------------------

@app.get("/api/ping")
def api_ping():
    """Ping for connection strength / RTT. Returns server time so client can compute RTT."""
    return {"ts": time.time(), "status": "ok"}


@app.get("/api/telemetry")
def api_telemetry():
    """Telemetry in the shape the React app expects (altitude, battery, signal, position, etc.)."""
    s = state_store
    rssi = s.rssi
    signal_max = 100
    if rssi is not None and isinstance(rssi, (int, float)):
        # Map RSSI (e.g. -30 to -90) to 0–100 if you have a scale; else pass through
        signal_strength = max(0, min(100, int(100 + (rssi + 50))))  # rough mapping
    else:
        signal_strength = None
    return {
        "altitude": s.altitude,
        "altitudeUnit": "m",
        "batteryPercent": None,
        "signalStrength": signal_strength,
        "signalMax": signal_max,
        "latitude": 0.0,
        "longitude": 0.0,
        "heading": 0.0,
        "speed": 0.0,
    }


@app.get("/api/scenic")
def api_scenic():
    """Scenic alerts. Return empty list; can later map from state_store.detections."""
    return []


# -----------------------------------------------------------------------
# SERVE REACT APP — catch-all must be last
# -----------------------------------------------------------------------

if os.path.exists(STATIC_DIR):
    assets_dir = os.path.join(STATIC_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    def serve_react(full_path: str):
        """Serve React index.html for all non-API routes (supports React Router)."""
        index = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index):
            return FileResponse(index)
        return {"error": "index.html not found in dist/"}
else:
    @app.get("/")
    def no_frontend():
        return {
            "status": "API running, frontend not deployed.",
            "instructions": [
                "1. On laptop: cd frontend && npm run build:pi",
                "2. scp -r dist/ horizonair@192.168.50.1:/home/horizonair/horizon-air/frontend/",
                "3. On Pi: cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000"
            ]
        }