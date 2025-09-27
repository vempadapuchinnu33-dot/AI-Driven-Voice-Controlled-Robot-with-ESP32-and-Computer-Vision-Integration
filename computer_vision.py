#!/usr/bin/env python3
"""
Computer Vision Module for AI-Driven Voice Controlled Robot
Handles object detection and image processing from robot camera
"""

import cv2
import numpy as np
import threading
import time
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class DetectedObject:
    """Data class for detected objects"""
    name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x, y, width, height)
    center: Tuple[int, int]
    area: int

class ComputerVision:
    def __init__(self, camera_url: str = "http://192.168.1.100:81/stream"):
        """
        Initialize the computer vision module
        
        Args:
            camera_url (str): URL of the robot's camera stream
        """
        self.camera_url = camera_url
        self.cap = None
        self.is_running = False
        self.frame_lock = threading.Lock()
        self.current_frame = None
        self.detected_objects = []
        
        # Load YOLO model for object detection
        self.load_yolo_model()
        
        # Color detection parameters
        self.color_ranges = {
            'red': ([0, 50, 50], [10, 255, 255]),
            'green': ([40, 50, 50], [80, 255, 255]),
            'blue': ([100, 50, 50], [130, 255, 255]),
            'yellow': ([20, 50, 50], [40, 255, 255]),
            'orange': ([10, 50, 50], [20, 255, 255])
        }
        
        logging.info("Computer vision module initialized")
    
    def load_yolo_model(self):
        """Load YOLO model for object detection"""
        try:
            # In a real implementation, you would download and use actual YOLO weights
            # For this demo, we'll use a simplified approach with OpenCV's built-in classifiers
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            self.body_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_fullbody.xml')
            
            # COCO class names (subset)
            self.class_names = [
                'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck',
                'boat', 'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench',
                'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra',
                'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
                'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove',
                'skateboard', 'surfboard', 'tennis racket', 'bottle', 'wine glass', 'cup',
                'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich', 'orange',
                'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
                'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
                'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
                'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier',
                'toothbrush'
            ]
            
            logging.info("Object detection models loaded")
        except Exception as e:
            logging.error(f"Failed to load object detection models: {e}")
    
    def start_camera(self) -> bool:
        """
        Start the camera stream
        
        Returns:
            bool: True if camera started successfully, False otherwise
        """
        try:
            self.cap = cv2.VideoCapture(self.camera_url)
            if not self.cap.isOpened():
                # Fallback to default camera (for testing)
                self.cap = cv2.VideoCapture(0)
            
            if self.cap.isOpened():
                self.is_running = True
                self.camera_thread = threading.Thread(target=self._camera_loop)
                self.camera_thread.daemon = True
                self.camera_thread.start()
                logging.info("Camera stream started")
                return True
            else:
                logging.error("Failed to open camera")
                return False
        except Exception as e:
            logging.error(f"Error starting camera: {e}")
            return False
    
    def stop_camera(self):
        """Stop the camera stream"""
        self.is_running = False
        if hasattr(self, 'camera_thread'):
            self.camera_thread.join()
        if self.cap:
            self.cap.release()
        logging.info("Camera stream stopped")
    
    def _camera_loop(self):
        """Main camera processing loop"""
        while self.is_running:
            try:
                ret, frame = self.cap.read()
                if ret:
                    with self.frame_lock:
                        self.current_frame = frame.copy()
                    
                    # Process frame for object detection
                    self.process_frame(frame)
                else:
                    logging.warning("Failed to read frame from camera")
                    time.sleep(0.1)
            except Exception as e:
                logging.error(f"Error in camera loop: {e}")
                time.sleep(0.1)
    
    def process_frame(self, frame: np.ndarray):
        """
        Process a single frame for object detection
        
        Args:
            frame (np.ndarray): Input frame
        """
        detected_objects = []
        
        # Convert to grayscale for some detections
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces (as proxy for person detection)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
        for (x, y, w, h) in faces:
            obj = DetectedObject(
                name='person',
                confidence=0.8,
                bbox=(x, y, w, h),
                center=(x + w//2, y + h//2),
                area=w * h
            )
            detected_objects.append(obj)
        
        # Detect colored objects (balls, etc.)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        for color_name, (lower, upper) in self.color_ranges.items():
            lower = np.array(lower)
            upper = np.array(upper)
            mask = cv2.inRange(hsv, lower, upper)
            
            # Find contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 500:  # Minimum area threshold
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # Determine object type based on shape
                    aspect_ratio = w / h
                    if 0.8 <= aspect_ratio <= 1.2:  # Roughly circular
                        object_name = f"{color_name}_ball"
                    else:
                        object_name = f"{color_name}_object"
                    
                    obj = DetectedObject(
                        name=object_name,
                        confidence=0.7,
                        bbox=(x, y, w, h),
                        center=(x + w//2, y + h//2),
                        area=area
                    )
                    detected_objects.append(obj)
        
        # Update detected objects
        self.detected_objects = detected_objects
    
    def find_object(self, object_name: str) -> Optional[DetectedObject]:
        """
        Find a specific object in the current frame
        
        Args:
            object_name (str): Name of the object to find
            
        Returns:
            DetectedObject: The detected object or None if not found
        """
        object_name = object_name.lower()
        
        for obj in self.detected_objects:
            if object_name in obj.name.lower():
                return obj
        
        return None
    
    def get_largest_object(self, object_type: str = None) -> Optional[DetectedObject]:
        """
        Get the largest detected object of a specific type
        
        Args:
            object_type (str): Type of object to find (optional)
            
        Returns:
            DetectedObject: The largest object or None if not found
        """
        candidates = self.detected_objects
        
        if object_type:
            object_type = object_type.lower()
            candidates = [obj for obj in candidates if object_type in obj.name.lower()]
        
        if not candidates:
            return None
        
        return max(candidates, key=lambda obj: obj.area)
    
    def get_object_direction(self, obj: DetectedObject, frame_width: int = 640) -> str:
        """
        Determine the direction of an object relative to the camera center
        
        Args:
            obj (DetectedObject): The detected object
            frame_width (int): Width of the camera frame
            
        Returns:
            str: Direction ('left', 'center', 'right')
        """
        center_x = obj.center[0]
        frame_center = frame_width // 2
        threshold = frame_width * 0.1  # 10% threshold
        
        if center_x < frame_center - threshold:
            return 'left'
        elif center_x > frame_center + threshold:
            return 'right'
        else:
            return 'center'
    
    def get_current_frame(self) -> Optional[np.ndarray]:
        """
        Get the current camera frame
        
        Returns:
            np.ndarray: Current frame or None if not available
        """
        with self.frame_lock:
            return self.current_frame.copy() if self.current_frame is not None else None
    
    def draw_detections(self, frame: np.ndarray) -> np.ndarray:
        """
        Draw detection boxes on the frame
        
        Args:
            frame (np.ndarray): Input frame
            
        Returns:
            np.ndarray: Frame with detection boxes drawn
        """
        result_frame = frame.copy()
        
        for obj in self.detected_objects:
            x, y, w, h = obj.bbox
            
            # Draw bounding box
            cv2.rectangle(result_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Draw label
            label = f"{obj.name} ({obj.confidence:.2f})"
            cv2.putText(result_frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Draw center point
            cv2.circle(result_frame, obj.center, 5, (0, 0, 255), -1)
        
        return result_frame

if __name__ == "__main__":
    # Test the computer vision module
    logging.basicConfig(level=logging.INFO)
    
    cv_module = ComputerVision()
    
    if cv_module.start_camera():
        try:
            while True:
                frame = cv_module.get_current_frame()
                if frame is not None:
                    # Draw detections
                    result_frame = cv_module.draw_detections(frame)
                    
                    # Display frame (for testing)
                    cv2.imshow('Robot Vision', result_frame)
                    
                    # Print detected objects
                    if cv_module.detected_objects:
                        print(f"Detected {len(cv_module.detected_objects)} objects:")
                        for obj in cv_module.detected_objects:
                            direction = cv_module.get_object_direction(obj)
                            print(f"  {obj.name} at {direction} (confidence: {obj.confidence:.2f})")
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        except KeyboardInterrupt:
            print("Stopping computer vision...")
        finally:
            cv_module.stop_camera()
            cv2.destroyAllWindows()
    else:
        print("Failed to start camera")

