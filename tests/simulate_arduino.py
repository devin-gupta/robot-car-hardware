#!/usr/bin/env python3
"""Simulate Arduino uploading images to the server."""
import cv2
import requests
import time
from datetime import datetime

# Server configuration
# >>> CHANGE THIS LINE: Use your Mac's local network IP to simulate the ESP32 request.
SERVER_URL = "http://10.5.47.110:8080/upload"

def capture_and_upload():
    """Capture an image from camera and upload it to the server."""
    # Open camera (0 is usually the default camera on Mac)
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open camera")
        return
    
    print(f"Starting image upload simulation to {SERVER_URL}")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            # Capture frame
            ret, frame = cap.read()
            
            if not ret:
                print(f"[{datetime.now()}] Error: Could not read frame")
                time.sleep(1)
                continue
            
            # Encode frame as JPEG
            _, img_encoded = cv2.imencode('.jpg', frame)
            img_bytes = img_encoded.tobytes()
            
            # Send POST request
            try:
                response = requests.post(
                    SERVER_URL,
                    data=img_bytes,
                    headers={'Content-Type': 'image/jpeg'},
                    timeout=5
                )
                
                if response.status_code == 200:
                    print(f"[{datetime.now()}] Image uploaded: {len(img_bytes)} bytes")
                else:
                    print(f"[{datetime.now()}] Error: Server returned status {response.status_code}")
            except requests.exceptions.RequestException as e:
                # This will catch "Connection Refused" and other network errors
                print(f"[{datetime.now()}] Error uploading image: {e}")
            
            # Wait 1 second before next capture
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\nStopping image upload simulation...")
    finally:
        cap.release()
        print("Camera released")

if __name__ == "__main__":
    capture_and_upload()