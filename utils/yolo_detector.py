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
        
        # Mint green color for dashed borders (#2A9D8F)
        mint_color = (42, 157, 143)  # RGB for #2A9D8F
        
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            class_name = det['class']
            confidence = det['confidence']
            
            # Draw dashed border rectangle with rounded corners
            # Since PIL doesn't support dashed lines directly, we'll draw multiple small segments
            # For a retro look, we'll use a thicker dashed pattern
            border_width = 2
            dash_length = 8
            gap_length = 4
            
            # Draw top border (dashed)
            for x in range(int(x1), int(x2), dash_length + gap_length):
                draw.rectangle([x, y1, min(x + dash_length, x2), y1 + border_width], 
                             fill=mint_color, outline=mint_color)
            
            # Draw bottom border (dashed)
            for x in range(int(x1), int(x2), dash_length + gap_length):
                draw.rectangle([x, y2 - border_width, min(x + dash_length, x2), y2], 
                             fill=mint_color, outline=mint_color)
            
            # Draw left border (dashed)
            for y in range(int(y1), int(y2), dash_length + gap_length):
                draw.rectangle([x1, y, x1 + border_width, min(y + dash_length, y2)], 
                             fill=mint_color, outline=mint_color)
            
            # Draw right border (dashed)
            for y in range(int(y1), int(y2), dash_length + gap_length):
                draw.rectangle([x2 - border_width, y, x2, min(y + dash_length, y2)], 
                             fill=mint_color, outline=mint_color)
            
            # Draw rounded corners (small circles at corners to simulate rounded rect)
            corner_radius = 12
            # Top-left corner
            draw.ellipse([x1, y1, x1 + corner_radius, y1 + corner_radius], 
                        fill=mint_color, outline=mint_color)
            # Top-right corner
            draw.ellipse([x2 - corner_radius, y1, x2, y1 + corner_radius], 
                        fill=mint_color, outline=mint_color)
            # Bottom-left corner
            draw.ellipse([x1, y2 - corner_radius, x1 + corner_radius, y2], 
                        fill=mint_color, outline=mint_color)
            # Bottom-right corner
            draw.ellipse([x2 - corner_radius, y2 - corner_radius, x2, y2], 
                        fill=mint_color, outline=mint_color)
            
            # Draw pill-shaped label above the box
            label = f"{class_name}: {confidence:.2f}"
            try:
                # Try to use a pixel font-like font, fallback to default
                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 14)
                except:
                    try:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf", 14)
                    except:
                        font = ImageFont.load_default()
            except:
                font = ImageFont.load_default()
            
            # Get text size
            bbox = draw.textbbox((0, 0), label, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Calculate pill position (centered above the box)
            pill_width = text_width + 16
            pill_height = text_height + 8
            pill_x = (x1 + x2) / 2 - pill_width / 2
            pill_y = y1 - pill_height - 8
            
            # Draw white pill background (rounded rectangle)
            # Top rounded part
            draw.ellipse([pill_x, pill_y, pill_x + pill_height, pill_y + pill_height], 
                        fill=(255, 255, 255), outline=(255, 255, 255))
            draw.ellipse([pill_x + pill_width - pill_height, pill_y, 
                         pill_x + pill_width, pill_y + pill_height], 
                        fill=(255, 255, 255), outline=(255, 255, 255))
            # Rectangular middle
            draw.rectangle([pill_x + pill_height / 2, pill_y, 
                          pill_x + pill_width - pill_height / 2, pill_y + pill_height], 
                         fill=(255, 255, 255), outline=(255, 255, 255))
            
            # Draw label text in mint color
            text_x = pill_x + 8
            text_y = pill_y + (pill_height - text_height) / 2
            draw.text((text_x, text_y), label, fill=mint_color, font=font)
        
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

