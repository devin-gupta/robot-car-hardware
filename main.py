"""Main Flask server for Arduino camera feed."""
from flask import Flask, request, send_from_directory, render_template, jsonify
import os
import shutil
import requests
from datetime import datetime

from utils.config import (
    YOLO_ENABLED,
    YOLO_MODEL,
    YOLO_CONFIDENCE_THRESHOLD,
    YOLO_MAX_OBJECTS,
    UPLOAD_FOLDER,
    HOST,
    PORT,
    DEBUG,
    LATEST_IMAGE_PATH,
    LATEST_DETECTED_PATH,
    ROBOT_IP,
)

app = Flask(__name__)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize YOLO detector if enabled
yolo_detector = None
if YOLO_ENABLED:
    try:
        from utils.yolo_detector import YOLODetector
        yolo_detector = YOLODetector(model_path=YOLO_MODEL)
        if not yolo_detector.is_available():
            print("Warning: YOLO is enabled but model failed to load. Continuing without YOLO.")
            yolo_detector = None
    except ImportError as e:
        print(f"Warning: YOLO is enabled but required dependencies are not installed: {e}")
        print("Install YOLO dependencies with: pip install ultralytics opencv-python pillow numpy")
        print("Continuing without YOLO detection.")
        yolo_detector = None
else:
    print("YOLO is disabled. To enable, set environment variable: YOLO_ENABLED=true")

last_modified_time = None

# Settings storage (simple in-memory dict)
settings = {
    'brightness': 1.0,
    'yolo_enabled': True,
    'histogram_eq': False,
    'gaussian_blur': False
}


def apply_preprocessing(image_path, output_path):
    """Apply preprocessing settings to image."""
    try:
        import cv2
        from utils.yolo_detector import preprocess_image
        
        img = cv2.imread(image_path)
        if img is None:
            shutil.copy(image_path, output_path)
            return
        
        processed = preprocess_image(
            img,
            brightness=settings.get('brightness', 1.0),
            histogram_eq=settings.get('histogram_eq', False),
            gaussian_blur=settings.get('gaussian_blur', False)
        )
        cv2.imwrite(output_path, processed)
    except Exception as e:
        print(f"Preprocessing error: {e}")
        shutil.copy(image_path, output_path)


@app.route("/upload", methods=["POST"])
def upload():
    """Handle image upload from Arduino."""
    global last_modified_time
    image_data = request.data
    
    # Save original image
    with open(LATEST_IMAGE_PATH, "wb") as f:
        f.write(image_data)
    
    # Process with YOLO if enabled and available
    if yolo_detector and yolo_detector.is_available() and settings.get('yolo_enabled', True):
        try:
            annotated_img = yolo_detector.detect(
                LATEST_IMAGE_PATH,
                confidence_threshold=YOLO_CONFIDENCE_THRESHOLD,
                max_objects=YOLO_MAX_OBJECTS,
                brightness=settings.get('brightness', 1.0),
                histogram_eq=settings.get('histogram_eq', False),
                gaussian_blur=settings.get('gaussian_blur', False)
            )
            
            if annotated_img is not None:
                # Save annotated image (cv2 should be available since yolo_detector uses it)
                try:
                    import cv2
                    cv2.imwrite(LATEST_DETECTED_PATH, annotated_img)
                except ImportError:
                    # Fallback if cv2 is not available (shouldn't happen if YOLO works)
                    print("Error: cv2 not available for saving image")
                    apply_preprocessing(LATEST_IMAGE_PATH, LATEST_DETECTED_PATH)
            else:
                # If image couldn't be processed, apply preprocessing only
                apply_preprocessing(LATEST_IMAGE_PATH, LATEST_DETECTED_PATH)
        except Exception as e:
            print(f"YOLO processing error: {e}")
            # Fallback to preprocessing only
            apply_preprocessing(LATEST_IMAGE_PATH, LATEST_DETECTED_PATH)
    else:
        # If YOLO is disabled, apply preprocessing directly to latest.jpg for display
        apply_preprocessing(LATEST_IMAGE_PATH, LATEST_IMAGE_PATH)
        # Also update detected path for consistency
        shutil.copy(LATEST_IMAGE_PATH, LATEST_DETECTED_PATH)
    
    last_modified_time = datetime.now().timestamp()
    print(f"[{datetime.now()}] Image received: {len(image_data)} bytes")
    return "OK", 200


@app.route("/image_info")
def image_info():
    """Return timestamp of the latest image."""
    global last_modified_time
    return jsonify({"timestamp": last_modified_time})


@app.route("/settings", methods=["GET", "POST"])
def update_settings():
    """Get or update processing settings."""
    global settings
    if request.method == "POST":
        data = request.get_json()
        if 'brightness' in data:
            settings['brightness'] = float(data['brightness'])
        if 'yolo_enabled' in data:
            settings['yolo_enabled'] = bool(data['yolo_enabled'])
        if 'histogram_eq' in data:
            settings['histogram_eq'] = bool(data['histogram_eq'])
        if 'gaussian_blur' in data:
            settings['gaussian_blur'] = bool(data['gaussian_blur'])
        print(f"Settings updated: {settings}")
        return jsonify(settings)
    return jsonify(settings)


@app.route("/robot/move", methods=["POST"])
def robot_move():
    """Forward motor commands to ESP32 robot."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['fl', 'fr', 'bl', 'br']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields: fl, fr, bl, br"}), 400
        
        # Validate motor speeds are integers in valid range
        for field in required_fields:
            speed = data[field]
            if not isinstance(speed, int):
                return jsonify({"error": f"{field} must be an integer"}), 400
            if speed != 0 and (speed < -255 or speed > 255):
                return jsonify({"error": f"{field} must be between -255 and 255"}), 400
            if speed != 0 and abs(speed) < 230:
                return jsonify({"error": f"{field} must be 0 or between -255 and -230, or 230 and 255"}), 400
        
        # Forward to ESP32
        robot_url = f"http://{ROBOT_IP}/move"
        response = requests.post(
            robot_url,
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=2
        )
        
        if response.status_code == 200:
            return jsonify({"status": "ok", "robot_response": response.text}), 200
        else:
            return jsonify({"error": f"Robot returned status {response.status_code}", "robot_response": response.text}), response.status_code
            
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with robot: {e}")
        return jsonify({"error": "Failed to communicate with robot", "details": str(e)}), 503
    except Exception as e:
        print(f"Error in robot_move endpoint: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@app.route("/static/<path:filename>")
def serve_static(filename):
    """Serve static files with cache busting."""
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/")
def index():
    """Render the main camera feed page."""
    yolo_enabled = yolo_detector is not None and yolo_detector.is_available()
    image_url = "/static/latest_detected.jpg" if yolo_enabled else "/static/latest.jpg"
    
    return render_template(
        "index.html",
        yolo_enabled=yolo_enabled,
        image_url=image_url
    )


if __name__ == "__main__":
    print(f"Starting Arduino Camera Server...")
    print(f"YOLO Detection: {'Enabled' if yolo_detector and yolo_detector.is_available() else 'Disabled'}")
    print(f"Robot IP: {ROBOT_IP}")
    print(f"Server running on http://{HOST}:{PORT}")
    print(f"To enable YOLO, set environment variable: YOLO_ENABLED=true")
    app.run(host=HOST, port=PORT, debug=DEBUG)

