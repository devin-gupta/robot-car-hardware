# Arduino Camera Server

A Flask-based server for receiving and displaying images from an Arduino/ESP32 camera, with optional YOLO object detection.

## Features

- Clean, modern web interface with video call-style design
- Real-time image streaming from Arduino/ESP32
- Optional YOLO object detection with bounding boxes
- Easy configuration via environment variables

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

Note: If you don't plan to use YOLO detection, you can skip installing the YOLO dependencies (`ultralytics`, `opencv-python`). However, the server will still run without them if YOLO is disabled.

## Usage

### Basic Usage (Without YOLO)

Simply run the server:
```bash
python server.py
```

The server will start on `http://0.0.0.0:8080` and display images directly from your Arduino camera.

### With YOLO Object Detection

To enable YOLO object detection, set the environment variable:
```bash
export YOLO_ENABLED=true
python server.py
```

Or run it in one line:
```bash
YOLO_ENABLED=true python server.py
```

The YOLO model (`yolov8n.pt`) will be automatically downloaded on first run (approximately 6MB).

## Configuration

Configuration can be set via environment variables:

### YOLO Configuration
- `YOLO_ENABLED`: Enable/disable YOLO detection (default: `false`)
- `YOLO_MODEL`: YOLO model to use (default: `yolov8n.pt`)
- `YOLO_CONFIDENCE`: Confidence threshold for detection (default: `0.25`)
- `YOLO_MAX_OBJECTS`: Maximum number of objects to display (default: `5`)

### Server Configuration
- `HOST`: Server host (default: `0.0.0.0`)
- `PORT`: Server port (default: `8080`)
- `DEBUG`: Enable debug mode (default: `true`)

### Example with Custom Configuration

```bash
YOLO_ENABLED=true YOLO_CONFIDENCE=0.5 YOLO_MAX_OBJECTS=10 PORT=3000 python server.py
```

## Project Structure

```
hardware/
├── server.py           # Main Flask server
├── config.py           # Configuration settings
├── yolo_detector.py    # YOLO detection module
├── templates/
│   └── index.html      # Web interface template
├── static/             # Uploaded images directory
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## API Endpoints

- `POST /upload` - Upload image from Arduino
- `GET /` - Main web interface
- `GET /image_info` - Get latest image timestamp (JSON)
- `GET /static/<filename>` - Serve static images

## Arduino Integration

Send images via HTTP POST to `http://your-server-ip:8080/upload`:

```cpp
// Example Arduino/ESP32 code
#include <WiFi.h>
#include <HTTPClient.h>
#include <Camera.h>

void sendImage() {
    HTTPClient http;
    http.begin("http://your-server-ip:8080/upload");
    http.addHeader("Content-Type", "image/jpeg");
    
    camera_fb_t *fb = esp_camera_fb_get();
    http.POST(fb->buf, fb->len);
    esp_camera_fb_return(fb);
    
    http.end();
}
```

## Notes

- Images are saved to the `static/` directory
- The web interface automatically updates every 500ms
- If YOLO fails to process an image, it falls back to displaying the original image
- The server creates the `static/` directory automatically if it doesn't exist

