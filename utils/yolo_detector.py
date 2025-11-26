"""YOLO object detection module."""
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from ultralytics import YOLO


def preprocess_image(img, brightness=1.0, histogram_eq=False, gaussian_blur=False):
    """Apply preprocessing to image before YOLO detection.
    
    Args:
        img: Input image (numpy array)
        brightness: Brightness multiplier (1.0 = no change)
        histogram_eq: Apply histogram equalization
        gaussian_blur: Apply gaussian blur (3x3 kernel)
    
    Returns:
        Preprocessed image
    """
    result = img.copy()
    
    # Brightness adjustment
    if brightness != 1.0:
        result = cv2.convertScaleAbs(result, alpha=brightness, beta=0)
    
    # Histogram equalization
    if histogram_eq:
        # Convert to YUV and equalize Y channel
        yuv = cv2.cvtColor(result, cv2.COLOR_BGR2YUV)
        yuv[:,:,0] = cv2.equalizeHist(yuv[:,:,0])
        result = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)
    
    # Gaussian blur
    if gaussian_blur:
        result = cv2.GaussianBlur(result, (3, 3), 0)
    
    return result


class YOLODetector:
    """YOLO object detector for processing images."""
    
    def __init__(self, model_path="yolov8n.pt"):
        """Initialize YOLO detector with model."""
        self.model = None
        self.model_path = model_path
        self.load_model()
    
    def load_model(self):
        """Load YOLO model."""
        try:
            self.model = YOLO(self.model_path)
            print(f"YOLO model ({self.model_path}) loaded successfully")
        except Exception as e:
            print(f"Error loading YOLO model: {e}")
            self.model = None
    
    def is_available(self):
        """Check if YOLO model is available."""
        return self.model is not None
    
    def draw_bounding_boxes(self, image_path, results, max_objects=5):
        """Draw bounding boxes on image and return annotated image."""
        # Read the image
        img = cv2.imread(image_path)
        if img is None:
            return None
        
        # Convert BGR to RGB for PIL
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        draw = ImageDraw.Draw(pil_img)
        
        # Get detections, sorted by confidence
        detections = []
        if results and len(results) > 0:
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    confidence = float(box.conf[0])
                    class_id = int(box.cls[0])
                    class_name = result.names[class_id]
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    detections.append({
                        'class': class_name,
                        'confidence': confidence,
                        'bbox': [x1, y1, x2, y2]
                    })
        
        # Sort by confidence and take top N
        detections.sort(key=lambda x: x['confidence'], reverse=True)
        detections = detections[:max_objects]
        
        # Draw bounding boxes
        colors = {
            'person': (255, 0, 0),
            'car': (0, 255, 0),
            'bicycle': (0, 0, 255),
            'dog': (255, 165, 0),
            'cat': (255, 20, 147),
        }
        
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            class_name = det['class']
            confidence = det['confidence']
            
            # Get color for this class (default to cyan)
            color = colors.get(class_name, (0, 255, 255))
            
            # Draw rectangle
            draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
            
            # Draw label background
            label = f"{class_name}: {confidence:.2f}"
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
            except:
                try:
                    font = ImageFont.truetype("Arial.ttf", 16)
                except:
                    font = ImageFont.load_default()
            
            # Get text size
            bbox = draw.textbbox((0, 0), label, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Draw label background
            draw.rectangle([x1, y1 - text_height - 4, x1 + text_width + 4, y1], 
                          fill=color, outline=color)
            
            # Draw label text
            draw.text((x1 + 2, y1 - text_height - 2), label, fill=(255, 255, 255), font=font)
        
        # Convert back to numpy array and then to BGR for saving
        img_array = np.array(pil_img)
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        return img_bgr
    
    def detect(self, image_path, confidence_threshold=0.25, max_objects=5, 
               brightness=1.0, histogram_eq=False, gaussian_blur=False):
        """Run YOLO detection on an image and return annotated image."""
        if not self.is_available():
            return None
        
        try:
            # Read and preprocess image
            img = cv2.imread(image_path)
            if img is None:
                return None
            
            preprocessed_img = preprocess_image(img, brightness, histogram_eq, gaussian_blur)
            
            # Save preprocessed image temporarily for YOLO
            temp_path = image_path.replace('.jpg', '_preprocessed.jpg')
            cv2.imwrite(temp_path, preprocessed_img)
            
            # Run YOLO inference on preprocessed image
            results = self.model(temp_path, conf=confidence_threshold)
            
            # Draw bounding boxes on original image path (but use preprocessed for display)
            annotated_img = self.draw_bounding_boxes(temp_path, results, max_objects)
            
            # Count detections
            num_detections = 0
            if results and len(results) > 0 and results[0].boxes is not None:
                num_detections = len(results[0].boxes)
            
            print(f"[{datetime.now()}] YOLO detection completed: {num_detections} objects detected")
            
            return annotated_img
        except Exception as e:
            print(f"YOLO processing error: {e}")
            return None

