from picamera2 import Picamera2, Preview
from flask import Flask, Response
import threading
import cv2
import numpy as np
import time
import os

# -------------------------
# Camera Setup
# -------------------------
picam2 = Picamera2()
picam2.load_tuning_file("/usr/share/rpi-camera-assets/imx500_mobilenet_ssd.json")

# Preview configuration (shows on Pi screen)
config = picam2.create_preview_configuration(main={"size": (640, 480)})
picam2.configure(config)
picam2.start_preview(Preview.QTGL)
picam2.start()

# -------------------------
# Object Detection Setup
# -------------------------
target_objects = {"person", "cat", "dog", "bottle", "cup"}
detected_flags = {obj: False for obj in target_objects}
all_objects_detected = False
recording = False
clip_duration = 10
output_dir = "recorded_clips"
os.makedirs(output_dir, exist_ok=True)

# -------------------------
# Flask Video Streaming Setup
# -------------------------
app = Flask(__name__)

def gen_frames():
    global all_objects_detected, recording
    while True:
        # Capture frame
        frame = picam2.capture_array()  # RGB by default

        # --- Object Detection ---
        meta = picam2.capture_metadata()
        if "object_detect" in meta:
            detections = meta["object_detect"].get("detections", [])
            for obj in detected_flags:
                detected_flags[obj] = False
            for d in detections:
                label = d.get("label", "")
                if label in detected_flags:
                    detected_flags[label] = True
            all_objects_detected = all(detected_flags.values())
            print("All target objects detected:", all_objects_detected)

        # --- Automatic Recording ---
        if all_objects_detected and not recording:
            recording = True
            timestamp = int(time.time())
            filename = os.path.join(output_dir, f"clip_{timestamp}.mp4")
            print(f"Recording clip: {filename}")
            picam2.start_recording(filename)
            threading.Thread(target=lambda: stop_recording_after_delay(filename), daemon=True).start()

        # --- Convert RGB to BGR for correct colors in OpenCV / JPEG ---
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # Encode as JPEG
        ret, buffer = cv2.imencode('.jpg', frame_bgr)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

def stop_recording_after_delay(filename):
    global recording
    time.sleep(clip_duration)
    picam2.stop_recording()
    print(f"Finished recording clip: {filename}")
    recording = False

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def run_server():
    app.run(host='0.0.0.0', port=5000, threaded=True)

# -------------------------
# Start Flask server
# -------------------------
threading.Thread(target=run_server, daemon=True).start()
print("Streaming started! Connect your laptop to the Pi hotspot and open in browser:")
print("http://192.168.50.1:5000/video_feed")

# -------------------------
# Keep script running
# -------------------------
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    picam2.stop()
    print("Camera stopped")
