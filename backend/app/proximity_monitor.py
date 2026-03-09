"""
proximity_monitor.py
--------------------
Runs on the Raspberry Pi alongside main.py (uvicorn).

Reads RTT from state_store.rtt_ms — which is written by the React app's
useConnectionStrength hook via POST /api/ping/report every second.

No separate HTTP server needed. No heartbeat.py needed. No clock sync issues.
The app already shows the correct ping — this just acts on it.

Logic:
  RTT > 80ms  for 3 readings in a row  →  LOITER  (user too far)
  RTT < 50ms  for 3 readings in a row  →  resume GUIDED_NOGPS

Usage (from backend/app/):
    cd backend/app && python3 proximity_monitor.py

Requires:
    pip3 install pymavlink --break-system-packages
"""

import time
import sys
import os

# Import shared state from main.py (same directory)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from main import state_store

from pymavlink import mavutil

# =============================
# CONFIG
# =============================

UART_PORT      = "/dev/serial0"
BAUD_RATE      = 57600

RTT_PAUSE      = 80    # ms — above this = user too far
RTT_RESUME     = 50    # ms — below this = user back in range

PAUSE_STRIKES  = 3     # consecutive bad readings before pausing
RESUME_STRIKES = 3     # consecutive good readings before resuming

# If no RTT update received in this many seconds, treat as lost
STALE_TIMEOUT  = 5.0

# =============================


def classify(rtt_ms):
    if rtt_ms is None:        return "NO DATA", "⚪"
    if rtt_ms < RTT_RESUME:   return "CLOSE",   "🟢"
    if rtt_ms < RTT_PAUSE:    return "OK",       "🟢"
    return                           "TOO FAR",  "🔴"


def rtt_bar(rtt_ms):
    if rtt_ms is None:        return "[????]"
    if rtt_ms < RTT_RESUME:   return "[▓▓▓▓]"
    if rtt_ms < RTT_PAUSE:    return "[▓▓▓░]"
    if rtt_ms < 120:          return "[▓▓░░]"
    return                           "[▓░░░]"


def connect_mavlink():
    print("[MAVLink] Connecting to flight controller...")
    master = mavutil.mavlink_connection(UART_PORT, baud=BAUD_RATE)
    master.wait_heartbeat()
    print("[MAVLink] Connected.\n")
    return master


def main():
    master = connect_mavlink()

    mission_paused = False
    pause_strikes  = 0
    resume_strikes = 0

    print(f"[PROXIMITY] Reading RTT from app via state_store.rtt_ms")
    print(f"[PROXIMITY] Thresholds:")
    print(f"  Pause  > {RTT_PAUSE}ms  x{PAUSE_STRIKES} in a row")
    print(f"  Resume < {RTT_RESUME}ms  x{RESUME_STRIKES} in a row")
    print(f"[PROXIMITY] Open the app on any device to start proximity gating.\n")

    while True:
        ts  = time.strftime("%H:%M:%S")
        rtt = state_store.rtt_ms
        age = time.time() - state_store.last_update

        # Treat stale data (app closed / out of range) as a failed reading
        if age > STALE_TIMEOUT:
            rtt = None

        level, emoji = classify(rtt)
        is_bad       = level in ("TOO FAR", "NO DATA")

        rtt_str = f"{rtt:.0f}ms" if rtt is not None else "no data"
        print(f"[{ts}] {rtt_bar(rtt)}  RTT: {rtt_str:>8s}  {emoji} {level}", end="")

        if is_bad:
            pause_strikes  += 1
            resume_strikes  = 0
            print(f"  — strike {pause_strikes}/{PAUSE_STRIKES}")
        else:
            resume_strikes += 1
            pause_strikes   = 0
            print()

        # Pause after 3 consecutive bad readings
        if not mission_paused and pause_strikes >= PAUSE_STRIKES:
            print(f"\n  🛑 Switching to LOITER — user too far or app closed")
            master.set_mode_apm("LOITER")
            mission_paused = True
            pause_strikes  = 0

        # Resume after 3 consecutive good readings
        elif mission_paused and resume_strikes >= RESUME_STRIKES:
            print(f"\n  ✅ Resuming GUIDED_NOGPS — user back in range")
            master.set_mode_apm("GUIDED_NOGPS")
            mission_paused  = False
            resume_strikes  = 0

        if mission_paused:
            remaining = RESUME_STRIKES - resume_strikes
            print(f"  [PAUSED] Need {remaining} more reading(s) under {RTT_RESUME}ms to resume")

        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[PROXIMITY] Monitor stopped.")
