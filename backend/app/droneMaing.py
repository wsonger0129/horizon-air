"""
droneMain.py
------------
HorizonAir autonomous drone controller.

Local coordinate system:
  - Origin (0, 0) = drone's position on the ground at boot time
  - All movement is in meters: north_m (forward) and east_m (right)
  - No GPS required — MTF-01 optical flow handles position hold

Altitude cap:
  - MAX_ALTITUDE_M = 1.98 m (6.5 feet) — hard ceiling, never commanded higher
  - Keeps drone in visual line of sight for safety

Flight mode:
  - Always GUIDED_NOGPS — optical flow handles position hold and navigation
  - GPS receiver (BE-880) is used ONLY to read drone coordinates for
    proximity distance calculation vs phone GPS. It does not affect flight.

Test mode (TEST_MODE = True):
  - Ignores Flask waypoint, auto-sets end point to (5, 0) — 5m straight ahead
  - Set TEST_MODE = False to use the waypoint from the web app

API (FastAPI backend):
  - Reads /drone/state from PI_API (waypoint, commands, phone GPS, RTT).
  - Default: http://127.0.0.1:8000. For HTTPS (run_https.sh) set:
      HORIZON_PI_API=https://127.0.0.1:8443
    Self-signed cert is accepted (no verify). Same state store as backend/app/main.py.

Run:
    python3 droneMain.py
    # With HTTPS backend:
    HORIZON_PI_API=https://127.0.0.1:8443 python3 droneMain.py

Requires:
    pip3 install pymavlink --break-system-packages
    sudo apt install python3-picamera2 imx500-all -y   (for AI camera)
"""

import time
import subprocess
import re
import csv
import threading
import math
import sys
import os
import urllib.request
import json
import ssl

from pymavlink import mavutil

# Import shared state store from FastAPI backend (backend/app/main.py).
# Prefer backend so droneMain and API share the same state; fallback to local dummy.
state_store = None
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_backend = os.path.join(_repo_root, "backend")
if _backend not in sys.path:
    sys.path.insert(0, _backend)
try:
    from app.main import state_store
    print("[INIT] Connected to FastAPI state store (backend/app/main).")
except ImportError:
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from main import state_store
        print("[INIT] Connected to FastAPI state store (pyCam/main).")
    except ImportError:
        pass

if state_store is None:
    class _FallbackStore:
        def __init__(self):
            self.pos_north = 0.0;  self.pos_east = 0.0;  self.altitude = 0.0
            self.wp_north = None;  self.wp_east = None
            self.state = "IDLE";   self.armed = False
            self.avoiding = False; self.rc_override = False
            self.rssi = None;      self.lidar = None;  self.detections = []
            self.pending_command = None
            self.rtt_ms = None
            self.phone_lat = None; self.phone_lon = None
            self.phone_gps_update = None
            self.drone_lat = None; self.drone_lon = None
            import time; self.last_update = time.time()
    state_store = _FallbackStore()
    print("[INIT] FastAPI not found — using local state store.")

# =============================
# SETTINGS
# =============================

UART_PORT   = "/dev/serial0"
BAUD_RATE   = 57600

# --- Altitude ---
MAX_ALTITUDE_M  = 1.98      # 6.5 feet — hard ceiling
CRUISE_ALT_M    = 1.5       # normal flying altitude (under the cap)
CLIMB_RATE_MS   = 0.5       # m/s upward speed (gentle for low altitude)

# --- Test mode ---
TEST_MODE           = True   # Set False to require waypoint from web app
TEST_WAYPOINT_NORTH = 5.0    # meters forward in test mode
TEST_WAYPOINT_EAST  = 0.0

# --- Navigation ---
WAYPOINT_ACCEPT_RADIUS = 0.4    # meters — how close = "arrived"
FLY_SPEED_MS           = 0.8    # m/s horizontal cruise speed
POSITION_SEND_HZ       = 10     # how often to resend velocity command

# --- Safety ---
SAFE_LIDAR_DISTANCE = 0.5   # meters — lidar brake threshold (downward sensor)
LOOP_HZ             = 10    # main loop rate

# --- WiFi ---
PAUSE_RSSI_THRESHOLD  = -72  # dBm
RESUME_RSSI_THRESHOLD = -68  # dBm

# --- Proximity: GPS-based (primary) ---
# Phone posts GPS to /drone/phone_position every 1s via the React app.
# Drone GPS is read from FC via GPS_RAW_INT MAVLink messages.
# Neither is used for flight — GUIDED_NOGPS + optical flow handles that.
MAX_FOLLOW_RADIUS_M   = 2.5   # meters — pause if user is further than this
RESUME_RADIUS_M       = 2   # meters — resume when user is back within this
GPS_STALE_TIMEOUT     = 5.0    # seconds — treat GPS as lost if no update

# --- Proximity: RTT-based fallback (used when GPS unavailable) ---
PROX_BASELINE_SAMPLES = 10     # number of 1s averaged readings to calibrate baseline
PROX_PAUSE_MULTIPLIER = 1.25   # pause if RTT > baseline * 125%
PROX_PAUSE_STRIKES    = 3      # consecutive bad readings before LOITER
PROX_RESUME_STRIKES   = 3      # consecutive good readings before resuming
PROX_STALE_TIMEOUT    = 5.0    # seconds without RTT update = treat as lost
PROX_PINGS_PER_SECOND = 4      # pings averaged into each 1s measurement
PROX_CHECK_INTERVAL   = 1.0    # seconds between each averaged measurement
PI_API                = os.environ.get("HORIZON_PI_API", "http://192.168.50.1:8443")

# --- RC Override ---
RC_OVERRIDE_CHANNEL   = 5
RC_OVERRIDE_THRESHOLD = 1600   # µs
MANUAL_MODE           = "LOITER"

# --- AI Camera Avoidance ---
AVOID_BOX_AREA_THRESHOLD = 0.10
AVOID_CENTER_ZONE        = 0.35
AVOID_BACKUP_DURATION    = 1.5
AVOID_BACKUP_SPEED       = -0.5
AVOID_CONFIDENCE_MIN     = 0.50

LOG_FILE = "mission_log.csv"

# =============================


# -----------------------------------------------------------------------
# CAMERA DETECTOR (background thread)
# -----------------------------------------------------------------------

class CameraDetector:
    def __init__(self):
        self._detections = []
        self._lock = threading.Lock()
        self._running = False
        self._camera_available = False

        try:
            from picamera2 import Picamera2
            from picamera2.devices.imx500 import IMX500
            from picamera2.devices.imx500.postprocess_highernet import \
                postprocess_nanodet_detection
            self._Picamera2 = Picamera2
            self._IMX500 = IMX500
            self._postprocess = postprocess_nanodet_detection
            self._camera_available = True
            print("[CAMERA] IMX500 AI camera available.")
        except ImportError:
            print("[CAMERA] picamera2 not found — camera avoidance disabled.")

    def start(self):
        if not self._camera_available:
            return
        self._running = True
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def stop(self):
        self._running = False

    def get_detections(self):
        with self._lock:
            return list(self._detections)

    def _run(self):
        try:
            MODEL = "/usr/share/imx500-models/imx500_network_ssd_mobilenetv2_fpnlite_320x320_pp.rpk"
            imx500 = self._IMX500(MODEL)
            picam2 = self._Picamera2(imx500.camera_num)
            config = picam2.create_preview_configuration(
                controls={"FrameRate": 10}, buffer_count=6
            )
            picam2.start(config, show_preview=False)
            print("[CAMERA] Inference running.")
            while self._running:
                meta = picam2.capture_metadata()
                out  = imx500.get_outputs(meta, add_batch=True)
                if out is not None:
                    results = self._postprocess(
                        outputs=out, metadata=meta,
                        picam2=picam2, imx500=imx500,
                        conf=AVOID_CONFIDENCE_MIN
                    )
                    with self._lock:
                        self._detections = [
                            {"category": r.category, "conf": r.conf, "box": r.box}
                            for r in results
                        ]
                else:
                    with self._lock:
                        self._detections = []
                time.sleep(0.05)
            picam2.stop()
        except Exception as e:
            print(f"[CAMERA] Error: {e}")
            with self._lock:
                self._detections = []


# -----------------------------------------------------------------------
# MISSION CONTROLLER
# -----------------------------------------------------------------------

class MissionController:

    def __init__(self):
        self.master = self._connect()
        self.camera = CameraDetector()
        self.camera.start()

        # Local position tracking (dead reckoning from optical flow)
        self.pos_north = 0.0
        self.pos_east  = 0.0

        # Target waypoint in local coords
        self.wp_north  = None
        self.wp_east   = None

        # Flight state flags
        self.armed           = False
        self.mission_paused  = False
        self.avoiding        = False
        self.manual_override = False
        self.flight_state    = "IDLE"   # IDLE|ARMED|TAKEOFF|FLYING|LANDING|COMPLETE|ABORT

        # Proximity gating
        self.prox_paused         = False
        self.prox_pause_strikes  = 0
        self.prox_resume_strikes = 0
        self.prox_baseline       = None   # RTT baseline set during calibration
        self.prox_pause_thresh   = None   # baseline * PROX_PAUSE_MULTIPLIER
        self._last_prox_check    = 0.0

        # CSV log
        with open(LOG_FILE, "w") as f:
            csv.writer(f).writerow([
                "time", "pos_n", "pos_e", "alt",
                "wp_n", "wp_e", "state",
                "rssi", "lidar", "detections", "avoiding"
            ])

    # ------------------------------------------------------------------
    # CONNECTION
    # ------------------------------------------------------------------

    def _connect(self):
        print("[CONNECT] Connecting to flight controller...")
        master = mavutil.mavlink_connection(UART_PORT, baud=BAUD_RATE)
        master.wait_heartbeat()
        print("[CONNECT] Heartbeat received.")
        return master

    # ------------------------------------------------------------------
    # MODE / ARM
    # ------------------------------------------------------------------

    def _set_mode(self, mode):
        mode_id = self.master.mode_mapping().get(mode)
        if mode_id is None:
            print(f"[MODE] Unknown mode: {mode}")
            return
        self.master.mav.set_mode_send(
            self.master.target_system,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id
        )
        print(f"[MODE] → {mode}")

    def _arm(self):
        print("[ARM] Arming...")
        self.master.mav.command_long_send(
            self.master.target_system, self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0, 1, 0, 0, 0, 0, 0, 0
        )
        for _ in range(20):
            msg = self.master.recv_match(type="HEARTBEAT", blocking=True, timeout=1)
            if msg and (msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED):
                self.armed = True
                print("[ARM] Armed.")
                return True
            time.sleep(0.3)
        print("[ARM] Failed to arm.")
        return False

    def _disarm(self):
        self.master.mav.command_long_send(
            self.master.target_system, self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0, 0, 0, 0, 0, 0, 0, 0
        )
        self.armed = False
        print("[DISARM] Disarmed.")

    # ------------------------------------------------------------------
    # ALTITUDE
    # ------------------------------------------------------------------

    def _get_altitude(self):
        msg = self.master.recv_match(type="LOCAL_POSITION_NED", blocking=False)
        if msg:
            return abs(msg.z)
        return None

    def _get_lidar(self):
        msg = self.master.recv_match(type="DISTANCE_SENSOR", blocking=False)
        if msg:
            return msg.current_distance / 100.0
        return None

    # ------------------------------------------------------------------
    # LOCAL POSITION (optical flow)
    # ------------------------------------------------------------------

    def _update_local_position(self):
        msg = self.master.recv_match(type="LOCAL_POSITION_NED", blocking=False)
        if msg:
            self.pos_north = msg.x
            self.pos_east  = msg.y
            return abs(msg.z)
        return None

    # ------------------------------------------------------------------
    # VELOCITY COMMANDS
    # ------------------------------------------------------------------

    def _send_velocity_ned(self, vn, ve, vd):
        alt = self._get_altitude()
        if alt is not None and vd < 0:
            if alt >= MAX_ALTITUDE_M:
                vd = 0
                print(f"[ALT CAP] At {alt:.2f}m — climb blocked (cap={MAX_ALTITUDE_M}m)")
        self.master.mav.set_position_target_local_ned_send(
            0,
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_FRAME_LOCAL_NED,
            0b0000111111000111,
            0, 0, 0,
            vn, ve, vd,
            0, 0, 0,
            0, 0
        )

    def _send_velocity_body(self, vx, vy, vz):
        alt = self._get_altitude()
        if alt is not None and vz < 0:
            if alt >= MAX_ALTITUDE_M:
                vz = 0
        self.master.mav.set_position_target_local_ned_send(
            0,
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_FRAME_BODY_OFFSET_NED,
            0b0000111111000111,
            0, 0, 0,
            vx, vy, vz,
            0, 0, 0,
            0, 0
        )

    # ------------------------------------------------------------------
    # TAKEOFF
    # ------------------------------------------------------------------

    def _takeoff(self):
        target = min(CRUISE_ALT_M, MAX_ALTITUDE_M)
        print(f"[TAKEOFF] Climbing to {target:.2f}m (cap={MAX_ALTITUDE_M}m)")
        self._set_mode("GUIDED_NOGPS")
        time.sleep(0.5)

        deadline = time.time() + 15
        while time.time() < deadline:
            if self.manual_override:
                return False
            alt = self._get_altitude() or 0
            print(f"  Alt: {alt:.2f}m / {target:.2f}m", end="\r")
            if alt >= target - 0.15:
                print(f"\n[TAKEOFF] Reached {alt:.2f}m")
                return True
            vd = -CLIMB_RATE_MS if alt < MAX_ALTITUDE_M else 0
            self._send_velocity_ned(0, 0, vd)
            time.sleep(1.0 / POSITION_SEND_HZ)

        print("\n[TAKEOFF] Timeout")
        return False

    # ------------------------------------------------------------------
    # NAVIGATE TO WAYPOINT
    # ------------------------------------------------------------------

    def _fly_to_waypoint(self):
        if self.wp_north is None:
            return False

        print(f"[NAV] Flying to ({self.wp_north:.1f}m N, {self.wp_east:.1f}m E)")
        interval = 1.0 / POSITION_SEND_HZ

        while True:
            if self.manual_override:
                return False

            alt = self._update_local_position()

            dn = self.wp_north - self.pos_north
            de = self.wp_east  - self.pos_east
            dist = math.sqrt(dn**2 + de**2)

            print(f"  Dist: {dist:.2f}m  Pos:({self.pos_north:.1f},{self.pos_east:.1f})", end="\r")

            if dist < WAYPOINT_ACCEPT_RADIUS:
                print(f"\n[NAV] Waypoint reached.")
                return True

            if not self.avoiding:
                blocked, desc = self._check_camera_obstacle()
                if blocked:
                    print(f"\n[AVOID] {desc}")
                    self._execute_avoidance()
                    continue

            scale = FLY_SPEED_MS / dist
            vn = dn * scale
            ve = de * scale

            curr_alt = alt or 0
            target_alt = min(CRUISE_ALT_M, MAX_ALTITUDE_M)
            vd = 0
            if curr_alt < target_alt - 0.1:
                vd = -CLIMB_RATE_MS
            elif curr_alt > target_alt + 0.1:
                vd = CLIMB_RATE_MS

            self._send_velocity_ned(vn, ve, vd)
            time.sleep(interval)

    # ------------------------------------------------------------------
    # LANDING
    # ------------------------------------------------------------------

    def _land(self):
        print("[LAND] Descending...")
        deadline = time.time() + 20
        while time.time() < deadline:
            alt = self._get_altitude() or 0
            print(f"  Alt: {alt:.2f}m", end="\r")
            if alt < 0.15:
                print("\n[LAND] Touchdown.")
                break
            self._send_velocity_ned(0, 0, CLIMB_RATE_MS)
            time.sleep(0.1)
        self._set_mode("LAND")
        time.sleep(2)

    # ------------------------------------------------------------------
    # CAMERA AVOIDANCE
    # ------------------------------------------------------------------

    def _check_camera_obstacle(self):
        for det in self.camera.get_detections():
            x, y, w, h = det["box"]
            area = w * h
            if area < AVOID_BOX_AREA_THRESHOLD:
                continue
            center_x = x + w / 2.0
            if abs(center_x - 0.5) < AVOID_CENTER_ZONE:
                return True, f"{det['category']} conf={det['conf']:.2f} area={area:.2f}"
        return False, ""

    def _execute_avoidance(self):
        self.avoiding = True
        self._set_mode("BRAKE")
        time.sleep(0.8)
        self._set_mode("GUIDED_NOGPS")
        end = time.time() + AVOID_BACKUP_DURATION
        while time.time() < end:
            self._send_velocity_body(AVOID_BACKUP_SPEED, 0, 0)
            time.sleep(0.1)
        self._set_mode("LOITER")
        time.sleep(1.0)
        still, _ = self._check_camera_obstacle()
        if not still:
            self._set_mode("GUIDED_NOGPS")
            self.avoiding = False

    # ------------------------------------------------------------------
    # PROXIMITY CHECK (GPS primary, RTT fallback)
    #
    # GPS:  Phone posts lat/lon to /drone/phone_position every 1s via app.
    #       Drone lat/lon is read from FC GPS_RAW_INT messages.
    #       Haversine formula gives real distance in meters.
    #       Neither coordinate is used for flight — only for this check.
    #
    # RTT:  Fallback when GPS is unavailable (indoors, no fix).
    #       Averaged pings vs dynamic baseline calibrated at startup.
    # ------------------------------------------------------------------

    def _haversine(self, lat1, lon1, lat2, lon2):
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _get_api_state(self):
        """Fetch /drone/state from local API. Supports HTTP and HTTPS."""
        try:
            url = f"{PI_API}/drone/state"
            req = urllib.request.Request(url)
            if url.startswith("https://"):
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with urllib.request.urlopen(req, timeout=1, context=ctx) as resp:
                    return json.loads(resp.read())
            with urllib.request.urlopen(req, timeout=1) as resp:
                return json.loads(resp.read())
        except Exception:
            return None

    def _get_gps_distance(self):
        """
        Returns distance in meters between phone and drone.
        Phone GPS comes from /drone/phone_position (posted by React app).
        Drone GPS comes from FC GPS_RAW_INT (read in _sync_state).
        Returns None if either source is missing or stale.
        """
        data = self._get_api_state()
        if data is None:
            return None
        phone_lat  = data.get("phone_lat")
        phone_lon  = data.get("phone_lon")
        gps_update = data.get("phone_gps_update")


        # request GPS location
        connection = mavutil.mavlink_connection(UART_PORT, baud=BAUD_RATE)    
        connection.mav.command_long_send(
            connection.target_system,
            connection.target_component,
            mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
            0,
            mavutil.mavlink.MAVLINK_MSG_ID_GPS_RAW_INT,
            500000,   # interval in microseconds (0.5s)
            0, 0, 0, 0, 0
        )
        msg = connection.recv_match(type='GPS_RAW_INT', blocking=True)
        if msg:
            print("GPS status:", msg.fix_type)
            print("Satellites:", msg.satellites_visible)
            print("Lat:", msg.lat / 1e7)
            print("Lon:", msg.lon / 1e7)
            print()
            drone_lat  = msg.lat / 1e7
            drone_lon  = msg.lon / 1e7
            while True:
                print()
                time.sleep(1)

        if any(v is None for v in (phone_lat, phone_lon, drone_lat, drone_lon)):
            return None
        if gps_update is not None and time.time() - gps_update > GPS_STALE_TIMEOUT:
            return None
        return self._haversine(phone_lat, phone_lon, drone_lat, drone_lon)

    def _get_rtt(self):
        data = self._get_api_state()
        if data is None:
            return None, None
        return data.get("rtt_ms"), data.get("last_update")

    def _get_averaged_rtt(self):
        """Collect PROX_PINGS_PER_SECOND RTT readings over 1 second and average them."""
        samples = []
        interval = PROX_CHECK_INTERVAL / PROX_PINGS_PER_SECOND
        for _ in range(PROX_PINGS_PER_SECOND):
            rtt, last_update = self._get_rtt()
            if rtt is not None:
                if last_update is None or time.time() - last_update <= PROX_STALE_TIMEOUT:
                    samples.append(rtt)
            time.sleep(interval)
        return sum(samples) / len(samples) if samples else None

    def _calibrate_proximity(self):
        """
        Collect PROX_BASELINE_SAMPLES averaged RTT readings at startup.
        Establishes the RTT baseline used as fallback when GPS is unavailable.
        Always runs — even if GPS is available, fallback should be ready.
        """
        print(f"\n[PROX] Calibrating RTT baseline — collecting {PROX_BASELINE_SAMPLES} readings")
        print(f"[PROX] Each reading averages {PROX_PINGS_PER_SECOND} pings over 1 second.")
        print("[PROX] Make sure the app is open and connected.\n")

        samples = []
        attempts = 0
        while len(samples) < PROX_BASELINE_SAMPLES and attempts < PROX_BASELINE_SAMPLES * 3:
            attempts += 1
            avg_rtt = self._get_averaged_rtt()
            if avg_rtt is None:
                print(f"  [{len(samples)}/{PROX_BASELINE_SAMPLES}] No data — waiting for app...")
                continue
            samples.append(avg_rtt)
            print(f"  [{len(samples)}/{PROX_BASELINE_SAMPLES}] Avg RTT: {avg_rtt:.1f}ms")

        if len(samples) < PROX_BASELINE_SAMPLES:
            print("[PROX] WARNING: RTT baseline failed. RTT fallback disabled.")
            self.prox_baseline     = None
            self.prox_pause_thresh = None
        else:
            self.prox_baseline     = sum(samples) / len(samples)
            self.prox_pause_thresh = self.prox_baseline * PROX_PAUSE_MULTIPLIER
            print(f"\n[PROX] RTT baseline:     {self.prox_baseline:.1f}ms")
            print(f"[PROX] RTT pause thresh: >{self.prox_pause_thresh:.1f}ms")

        print(f"[PROX] GPS:      pause >{MAX_FOLLOW_RADIUS_M}m | resume <{RESUME_RADIUS_M}m")
        print(f"[PROX] Fallback: {'RTT' if self.prox_baseline else 'DISABLED — no GPS, no RTT'}\n")

    def _check_proximity(self):
        """
        Called every loop tick. Rate-limited to once per PROX_CHECK_INTERVAL.
        Primary:  GPS distance (phone vs drone). Pause > 30m, resume < 25m.
        Fallback: Averaged RTT vs baseline * 125%. Used when GPS unavailable.
        Both use 3-strike rule. Only active during FLYING or TAKEOFF.
        Returns True if mission should be paused.
        """
        if self.flight_state not in ("FLYING", "TAKEOFF"):
            return self.prox_paused

        now = time.time()
        if now - self._last_prox_check < PROX_CHECK_INTERVAL:
            return self.prox_paused
        self._last_prox_check = now

        # Try GPS first
        dist = self._get_gps_distance()

        if dist is not None:
            is_bad     = dist > MAX_FOLLOW_RADIUS_M
            mode       = "GPS"
            val_str    = f"{dist:.1f}m"
            thresh_str = f"{MAX_FOLLOW_RADIUS_M}m"
        else:
            # Fall back to RTT
            if self.prox_baseline is None:
                return self.prox_paused
            avg_rtt    = self._get_averaged_rtt()
            is_bad     = avg_rtt is None or avg_rtt > self.prox_pause_thresh
            mode       = "RTT"
            val_str    = f"{avg_rtt:.1f}ms" if avg_rtt is not None else "no data"
            thresh_str = f"{self.prox_pause_thresh:.1f}ms"

        if is_bad:
            self.prox_pause_strikes  += 1
            self.prox_resume_strikes  = 0
            print(f"[PROX/{mode}] {val_str} > {thresh_str} — strike {self.prox_pause_strikes}/{PROX_PAUSE_STRIKES}")
        else:
            self.prox_resume_strikes += 1
            self.prox_pause_strikes   = 0
            print(f"[PROX/{mode}] {val_str} — OK ({self.prox_resume_strikes}/{PROX_RESUME_STRIKES})")

        if not self.prox_paused and self.prox_pause_strikes >= PROX_PAUSE_STRIKES:
            print(f"[PROX/{mode}] User too far — LOITER")
            self._set_mode("LOITER")
            self.prox_paused        = True
            self.mission_paused     = True
            self.prox_pause_strikes = 0

        elif self.prox_paused and self.prox_resume_strikes >= PROX_RESUME_STRIKES:
            print(f"[PROX/{mode}] Back in range ({val_str}) — resuming GUIDED_NOGPS")
            self._set_mode("GUIDED_NOGPS")
            self.prox_paused         = False
            self.mission_paused      = False
            self.prox_resume_strikes = 0

        return self.prox_paused

    # ------------------------------------------------------------------
    # RC OVERRIDE
    # ------------------------------------------------------------------

    def _check_rc_override(self):
        msg = self.master.recv_match(type="RC_CHANNELS", blocking=False)
        if msg:
            val = getattr(msg, f"chan{RC_OVERRIDE_CHANNEL}_raw", 0)
            return val > RC_OVERRIDE_THRESHOLD
        return self.manual_override

    def _handle_rc_override(self):
        on = self._check_rc_override()
        if on and not self.manual_override:
            print("\n[RC] Pilot override — LOITER")
            self._set_mode(MANUAL_MODE)
            self.manual_override = True
            self.mission_paused  = True
            self.avoiding        = False
        elif not on and self.manual_override:
            print("[RC] Override released — resuming")
            self.manual_override = False
            self.mission_paused  = False
        return self.manual_override

    # ------------------------------------------------------------------
    # WIFI RSSI
    # ------------------------------------------------------------------

    def _get_rssi(self):
        try:
            result = subprocess.run(
                ["iw", "dev", "wlan0", "station", "dump"],
                capture_output=True, text=True, timeout=1
            )
            match = re.search(r"signal:\s*(-\d+)", result.stdout)
            return int(match.group(1)) if match else None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # STATE SYNC → FastAPI
    # ------------------------------------------------------------------

    def _sync_state(self, rssi, lidar, detections):
        state_store.pos_north   = self.pos_north
        state_store.pos_east    = self.pos_east
        state_store.altitude    = self._get_altitude() or 0
        state_store.state       = self.flight_state
        state_store.armed       = self.armed
        state_store.avoiding    = self.avoiding
        state_store.rc_override = self.manual_override
        state_store.rssi        = rssi
        state_store.lidar       = lidar
        state_store.detections  = [d["category"] for d in detections]
        state_store.last_update = time.time()

        # Read drone GPS from FC — stored for proximity distance calculation only.
        # Not used for flight control (drone always flies in GUIDED_NOGPS).
        gps_msg = self.master.recv_match(type="GPS_RAW_INT", blocking=False)
        if gps_msg and gps_msg.fix_type >= 3:
            state_store.drone_lat = gps_msg.lat / 1e7
            state_store.drone_lon = gps_msg.lon / 1e7

    # ------------------------------------------------------------------
    # LOGGING
    # ------------------------------------------------------------------

    def _log(self, rssi, lidar, detections):
        with open(LOG_FILE, "a") as f:
            csv.writer(f).writerow([
                time.time(),
                round(self.pos_north, 2), round(self.pos_east, 2),
                round(self._get_altitude() or 0, 2),
                self.wp_north, self.wp_east,
                self.flight_state, rssi, lidar,
                "|".join(d["category"] for d in detections),
                self.avoiding
            ])

    # ------------------------------------------------------------------
    # CONSUME PENDING COMMANDS FROM API
    # ------------------------------------------------------------------

    def _consume_command(self):
        cmd = state_store.pending_command
        if cmd is None:
            return
        state_store.pending_command = None
        print(f"[CMD] Received command: {cmd}")
        if cmd == "abort":
            print("[CMD] ABORT — switching to LOITER")
            self._set_mode("LOITER")
            self.flight_state = "ABORT"
        elif cmd == "land":
            self.flight_state = "LANDING"

    # ------------------------------------------------------------------
    # MAIN SEQUENCE
    # ------------------------------------------------------------------

    def run(self):
        print("\n" + "="*55)
        print("  HORIZONAIR DRONE CONTROLLER")
        print(f"  Max altitude: {MAX_ALTITUDE_M}m ({MAX_ALTITUDE_M*3.281:.1f} ft)")
        print(f"  Flight mode:  GUIDED_NOGPS (optical flow)")
        print(f"  Proximity:    GPS primary, RTT fallback")
        print(f"  Test mode:    {TEST_MODE}")
        if TEST_MODE:
            print(f"  Test waypoint: {TEST_WAYPOINT_NORTH}m N, {TEST_WAYPOINT_EAST}m E")
        print("="*55 + "\n")

        # Set waypoint
        if TEST_MODE:
            self.wp_north = TEST_WAYPOINT_NORTH
            self.wp_east  = TEST_WAYPOINT_EAST
            state_store.wp_north = self.wp_north
            state_store.wp_east  = self.wp_east
            print(f"[INIT] Test waypoint: ({self.wp_north}, {self.wp_east})")
        else:
            print("[INIT] Waiting for waypoint from web app...")
            while state_store.wp_north is None:
                rssi = self._get_rssi()
                self._sync_state(rssi, None, [])
                time.sleep(0.5)
            self.wp_north = state_store.wp_north
            self.wp_east  = state_store.wp_east
            print(f"[INIT] Waypoint received: ({self.wp_north}, {self.wp_east})")

        # Calibrate RTT baseline for proximity fallback
        self._calibrate_proximity()

        # ── MAIN CONTROL LOOP ─────────────────────────────────────
        try:
            while True:
                rssi       = self._get_rssi()
                lidar      = self._get_lidar()
                detections = self.camera.get_detections()

                self._consume_command()

                # RC override always wins
                if self._handle_rc_override():
                    self._sync_state(rssi, lidar, detections)
                    self._log(rssi, lidar, detections)
                    time.sleep(0.1)
                    continue

                # Proximity check — pauses mission if user too far
                if self._check_proximity():
                    self._sync_state(rssi, lidar, detections)
                    self._log(rssi, lidar, detections)
                    time.sleep(1.0 / LOOP_HZ)
                    continue

                # Check if waypoint changed via app
                if not TEST_MODE:
                    if state_store.wp_north is not None:
                        self.wp_north = state_store.wp_north
                        self.wp_east  = state_store.wp_east

                # ── STATE MACHINE ─────────────────────────────────

                if self.flight_state == "IDLE":
                    if TEST_MODE or state_store.pending_command == "arm":
                        state_store.pending_command = None
                        self._set_mode("GUIDED_NOGPS")
                        if self._arm():
                            self.flight_state = "TAKEOFF"

                elif self.flight_state == "TAKEOFF":
                    if self._takeoff():
                        self.flight_state = "FLYING"
                    else:
                        self.flight_state = "ABORT"

                elif self.flight_state == "FLYING":
                    if lidar is not None and lidar < SAFE_LIDAR_DISTANCE:
                        print(f"[LIDAR] {lidar:.2f}m — BRAKE")
                        self._set_mode("BRAKE")
                    else:
                        if self._fly_to_waypoint():
                            self.flight_state = "LANDING"

                elif self.flight_state == "LANDING":
                    self._land()
                    self._disarm()
                    self._set_mode("LOITER")
                    self.flight_state = "COMPLETE"
                    print("[DONE] Mission complete.")

                elif self.flight_state == "COMPLETE":
                    pass   # Sit in LOITER, wait for next command

                elif self.flight_state == "ABORT":
                    self._set_mode("LOITER")

                self._sync_state(rssi, lidar, detections)
                self._log(rssi, lidar, detections)

                time.sleep(1.0 / LOOP_HZ)

        except KeyboardInterrupt:
            print("\n[ABORT] Ctrl+C — LOITER")
            self._set_mode("LOITER")

        except Exception as e:
            print(f"\n[ERROR] {e}")
            try:
                self._set_mode("LOITER")
            except Exception:
                pass
            raise


if __name__ == "__main__":
    controller = MissionController()
    controller.run()
