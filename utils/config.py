"""Configuration settings for the camera server."""
import os

# YOLO Configuration
YOLO_ENABLED = os.getenv("YOLO_ENABLED", "false").lower() == "true"
# Model path relative to utils directory
YOLO_MODEL = os.getenv("YOLO_MODEL", os.path.join(os.path.dirname(__file__), "yolov8n.pt"))
YOLO_CONFIDENCE_THRESHOLD = float(os.getenv("YOLO_CONFIDENCE", "0.25"))
YOLO_MAX_OBJECTS = int(os.getenv("YOLO_MAX_OBJECTS", "5"))

# Server Configuration
UPLOAD_FOLDER = "static"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# Image paths
LATEST_IMAGE_PATH = os.path.join(UPLOAD_FOLDER, "latest.jpg")
LATEST_DETECTED_PATH = os.path.join(UPLOAD_FOLDER, "latest_detected.jpg")

# Robot Configuration
ROBOT_IP = os.getenv("ROBOT_IP", "172.20.10.7")

