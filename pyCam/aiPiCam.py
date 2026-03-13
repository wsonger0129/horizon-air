from functools import lru_cache
import os
import threading
import time

import cv2
from flask import Flask, Response, jsonify
from picamera2 import Picamera2
from picamera2.devices import IMX500
from picamera2.devices.imx500 import NetworkIntrinsics

# -------------------------
# Config
# -------------------------
MODEL_PATH = "/usr/share/imx500-models/imx500_network_ssd_mobilenetv2_fpnlite_320x320_pp.rpk"
FRAME_SIZE = (640, 480)
JPEG_QUALITY = 75
THRESHOLD = 0.55
MAX_DETECTIONS = 10

target_objects = {"person", "cat", "dog", "bottle", "cup"}
detected_flags = {obj: False for obj in target_objects}
all_objects_detected = False

recording = False
clip_duration = 10
output_dir = "recorded_clips"
os.makedirs(output_dir, exist_ok=True)

app = Flask(__name__)

# -------------------------
# IMX500 / Picamera2 setup
# -------------------------
imx500 = IMX500(MODEL_PATH)
intrinsics = imx500.network_intrinsics

if not intrinsics:
    intrinsics = NetworkIntrinsics()
    intrinsics.task = "object detection"
elif intrinsics.task != "object detection":
    raise RuntimeError(f"Model task is {intrinsics.task!r}, not 'object detection'")

intrinsics.update_with_defaults()

picam2 = Picamera2(imx500.camera_num)
config = picam2.create_preview_configuration(
    main={"size": FRAME_SIZE},
    controls={"FrameRate": intrinsics.inference_rate},
    buffer_count=6,
)

imx500.show_network_fw_progress_bar()
picam2.start(config)

if getattr(intrinsics, "preserve_aspect_ratio", False):
    imx500.set_auto_aspect_ratio()

last_detections = []


# -------------------------
# Helpers
# -------------------------
class Detection:
    def __init__(self, coords, category, conf, metadata):
        self.category = category
        self.conf = float(conf)
        self.box = imx500.convert_inference_coords(coords, metadata, picam2)


@lru_cache
def get_labels():
    labels = intrinsics.labels or []
    if getattr(intrinsics, "ignore_dash_labels", False):
        labels = [label for label in labels if label and label != "-"]
    return labels


def parse_detections(metadata):
    global last_detections

    np_outputs = imx500.get_outputs(metadata, add_batch=True)
    input_w, input_h = imx500.get_input_size()

    if np_outputs is None:
        return last_detections

    # MobileNet SSD path from the official example
    boxes, scores, classes = np_outputs[0][0], np_outputs[1][0], np_outputs[2][0]

    if getattr(intrinsics, "bbox_normalization", False):
        boxes = boxes / input_h

    if getattr(intrinsics, "bbox_order", "yx") == "xy":
        boxes = boxes[:, [1, 0, 3, 2]]

    detections = []
    for box, score, category in zip(boxes, scores, classes):
        if float(score) > THRESHOLD:
            detections.append(Detection(box, category, score, metadata))
        if len(detections) >= MAX_DETECTIONS:
            break

    last_detections = detections
    return detections


def update_target_flags(detections):
    global all_objects_detected

    for obj in detected_flags:
        detected_flags[obj] = False

    labels = get_labels()

    for det in detections:
        idx = int(det.category)
        if 0 <= idx < len(labels):
            label = labels[idx]
            if label in detected_flags:
                detected_flags[label] = True

    all_objects_detected = all(detected_flags.values())


def draw_detections(frame_bgr, detections):
    labels = get_labels()

    for det in detections:
        if det.box is None:
            continue

        x, y, w, h = map(int, det.box)

        idx = int(det.category)
        label_name = labels[idx] if 0 <= idx < len(labels) else str(idx)
        label = f"{label_name} ({det.conf:.2f})"

        cv2.rectangle(frame_bgr, (x, y), (x + w, y + h), (0, 255, 0), 2)

        (text_width, text_height), baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
        )
        text_x = x + 5
        text_y = y + 15

        overlay = frame_bgr.copy()
        cv2.rectangle(
            overlay,
            (text_x, text_y - text_height),
            (text_x + text_width, text_y + baseline),
            (255, 255, 255),
            cv2.FILLED,
        )
        alpha = 0.30
        frame_bgr[:] = cv2.addWeighted(overlay, alpha, frame_bgr, 1 - alpha, 0)
        cv2.putText(
            frame_bgr,
            label,
            (text_x, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 255),
            1,
            cv2.LINE_AA,
        )

    return frame_bgr


def draw_status_overlay(frame_bgr):
    y = 22
    for obj in sorted(target_objects):
        status = "Y" if detected_flags[obj] else "N"
        color = (0, 220, 0) if detected_flags[obj] else (0, 0, 255)
        cv2.putText(
            frame_bgr,
            f"{obj}: {status}",
            (10, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
            cv2.LINE_AA,
        )
        y += 22

    overall_color = (0, 220, 0) if all_objects_detected else (0, 200, 255)
    cv2.putText(
        frame_bgr,
        f"all_objects_detected: {all_objects_detected}",
        (10, y + 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        overall_color,
        2,
        cv2.LINE_AA,
    )

    if recording:
        cv2.putText(
            frame_bgr,
            "REC",
            (frame_bgr.shape[1] - 70, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )

    return frame_bgr


def stop_recording_after_delay():
    global recording
    time.sleep(clip_duration)
    try:
        picam2.stop_recording()
        print("Finished recording clip")
    except Exception as e:
        print("Error stopping recording:", e)
    recording = False


# -------------------------
# Flask / CORS
# -------------------------
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


def gen_frames():
    global recording

    while True:
        metadata = picam2.capture_metadata()
        detections = parse_detections(metadata)
        update_target_flags(detections)

        frame = picam2.capture_array("main")  # RGB
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        frame_bgr = draw_detections(frame_bgr, detections)
        frame_bgr = draw_status_overlay(frame_bgr)

        if all_objects_detected and not recording:
            recording = True
            timestamp = int(time.time())
            filename = os.path.join(output_dir, f"clip_{timestamp}.mp4")
            print(f"Recording clip: {filename}")
            try:
                picam2.start_recording(filename)
                threading.Thread(target=stop_recording_after_delay, daemon=True).start()
            except Exception as e:
                print("Error starting recording:", e)
                recording = False

        ret, buffer = cv2.imencode(
            ".jpg",
            frame_bgr,
            [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY],
        )
        if not ret:
            continue

        frame_bytes = buffer.tobytes()
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n"
            b"Cache-Control: no-cache\r\n\r\n" + frame_bytes + b"\r\n"
        )


@app.route("/")
def index():
    return """
    <html>
      <head>
        <title>Pi Camera Stream</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>
          body {
            background: #111;
            color: white;
            font-family: Arial, sans-serif;
            text-align: center;
            margin: 0;
            padding: 20px;
          }
          img {
            max-width: 95vw;
            max-height: 85vh;
            border: 2px solid #444;
            border-radius: 8px;
          }
        </style>
      </head>
      <body>
        <h2>Raspberry Pi Camera Stream</h2>
        <img src="/video_feed" />
      </body>
    </html>
    """


@app.route("/video_feed")
def video_feed():
    return Response(
        gen_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/api/telemetry")
def api_telemetry():
    return jsonify({
        "altitude": 42,
        "altitudeUnit": "m",
        "batteryPercent": 78,
        "signalStrength": 4,
        "signalMax": 5,
    })


@app.route("/api/scenic")
def api_scenic():
    now_ms = int(time.time() * 1000)
    return jsonify([
        {
            "id": "1",
            "thumbnail": "",
            "description": "Wide mountain vista detected — clear view to the east.",
            "timestamp": now_ms - 2 * 60 * 1000,
            "location": {"lat": 33.647, "lng": -117.843},
            "confidence": 0.92,
        },
        {
            "id": "2",
            "thumbnail": "",
            "description": "Scenic clearing with lake view ahead.",
            "timestamp": now_ms - 8 * 60 * 1000,
            "location": {"lat": 33.648, "lng": -117.844},
            "confidence": 0.88,
        },
    ])


@app.route("/api/ping")
def api_ping():
    return jsonify({"ok": True, "ts": int(time.time() * 1000)})


if __name__ == "__main__":
    try:
        print("Streaming started.")
        print("Open: http://<PI_IP>:5000/")
        app.run(host="0.0.0.0", port=5000, threaded=True)
    finally:
        picam2.stop()
        print("Camera stopped")