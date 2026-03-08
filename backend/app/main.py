"""
HorizonAir — runs entirely on the Raspberry Pi Zero 2W.

Video pipeline (no ffmpeg — saves ~50MB RAM + significant CPU):
  rpicam-vid --codec mjpeg → stdout → FastAPI /stream endpoint
  IMX500 handles object detection on-chip.
  Pi CPU is barely involved in video encoding.

Serves:
  http://192.168.50.1:8000          → React app
  http://192.168.50.1:8000/stream   → MJPEG video stream
  http://192.168.50.1:8000/drone/*  → REST API

Run:
    uvicorn main:app --host 0.0.0.0 --port 8000
"""

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

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")


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

    def to_dict(self):
        return {
            "pos_north":       self.pos_north,
            "pos_east":        self.pos_east,
            "altitude":        self.altitude,
            "wp_north":        self.wp_north,
            "wp_east":         self.wp_east,
            "state":           self.state,
            "armed":           self.armed,
            "avoiding":        self.avoiding,
            "rc_override":     self.rc_override,
            "rssi":            self.rssi,
            "lidar":           self.lidar,
            "detections":      self.detections,
            "pending_command": self.pending_command,
            "last_update":     self.last_update,
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


# -----------------------------------------------------------------------
# STARTUP
# -----------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
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
    """Keeps WiFi radio active so iw station dump can read RSSI."""
    return {"ts": time.time()}


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
                "1. On laptop: cd frontend && npm run build",
                "2. scp -r dist/ horizonair@192.168.50.1:/home/horizonair/horizon-air/frontend/",
                "3. Restart uvicorn"
            ]
        }