#!/usr/bin/env python3
"""
Intruder Detection System for Jetson Nano
Uses YOLOv8 with TensorRT optimization for efficient object detection
Implements zone-based intrusion logic with alerts
"""

import os
import cv2
import time
import json
import numpy as np
import argparse
import logging
from datetime import datetime
from pathlib import Path
from threading import Thread
import queue

from ultralytics import YOLO
from shapely.geometry import Point, Polygon

# Alert modules
from utils.alert_manager import AlertManager
from utils.performance_monitor import PerformanceMonitor
from utils.zone_manager import ZoneManager
from utils.config_loader import ConfigLoader

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/detection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('IntruderDetection')

class IntruderDetectionSystem:
    def __init__(self, config_path="config/config.json"):
        """Initialize the intruder detection system"""
        # Load configuration
        self.config_loader = ConfigLoader(config_path)
        self.config = self.config_loader.load_config()
        
        # Initialize components
        self.setup_model()
        self.setup_camera()
        self.zone_manager = ZoneManager(self.config['zones'])
        self.alert_manager = AlertManager(self.config['alerts'])
        self.perf_monitor = PerformanceMonitor()
        
        # Setup processing queues for threaded operation
        self.frame_queue = queue.Queue(maxsize=self.config['system']['queue_size'])
        self.result_queue = queue.Queue(maxsize=self.config['system']['queue_size'])
        
        # Runtime variables
        self.running = False
        self.last_alert_time = 0
        self.frame_count = 0
        self.last_saved_frame = 0
        self.output_video = None
        
        logger.info("Intruder Detection System initialized")

    def setup_model(self):
        """Load and optimize the YOLOv8 model with TensorRT"""
        model_path = self.config['model']['path']
        
        logger.info(f"Loading YOLOv8 model from {model_path}")
        self.model = YOLO(model_path)
        
        # Apply TensorRT optimization if enabled
        if self.config['model']['use_tensorrt']:
            logger.info("Applying TensorRT optimization...")
            try:
                self.model.export(format='engine', device=0)
                logger.info("TensorRT optimization applied successfully")
            except Exception as e:
                logger.error(f"Failed to apply TensorRT optimization: {e}")
                logger.info("Falling back to regular model")
        
        # Set confidence threshold
        self.conf_threshold = self.config['model']['confidence_threshold']
        
        # Classes of interest (persons by default)
        self.target_classes = self.config['model']['target_classes']

    def setup_camera(self):
        """Initialize the camera source (RTSP or USB)"""
        source = self.config['camera']['source']
        logger.info(f"Setting up camera from source: {source}")
        
        # For RTSP streams
        if source.startswith('rtsp://'):
            self.cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
        # For USB cameras or local videos
        else:
            try:
                source = int(source)  # Try to convert to integer for USB camera index
            except ValueError:
                pass  # Keep as string if it's a file path
            self.cap = cv2.VideoCapture(source)
        
        # Set camera properties if specified
        if 'width' in self.config['camera'] and 'height' in self.config['camera']:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config['camera']['width'])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config['camera']['height'])
        
        if not self.cap.isOpened():
            raise ValueError(f"Failed to open camera source: {source}")
        
        # Get actual frame dimensions
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        logger.info(f"Camera initialized with resolution: {self.frame_width}x{self.frame_height}")
        
        # Setup output video if enabled
        if self.config['output']['save_video']:
            self.setup_output_video()

    def setup_output_video(self):
        """Setup output video writer"""
        output_dir = Path(self.config['output']['output_dir'])
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"detection_{timestamp}.mp4"
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = self.config['output']['output_fps'] or int(self.cap.get(cv2.CAP_PROP_FPS))
        
        self.output_video = cv2.VideoWriter(
            str(output_path), 
            fourcc, 
            fps, 
            (self.frame_width, self.frame_height)
        )
        logger.info(f"Output video will be saved to {output_path}")

    def capture_frames(self):
        """Thread function to capture frames from the camera"""
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                logger.error("Failed to capture frame from camera")
                if self.config['system']['reconnect_on_failure']:
                    logger.info("Attempting to reconnect to camera...")
                    self.setup_camera()
                    continue
                else:
                    self.running = False
                    break
            
            # Put frame in queue, drop if queue is full
            try:
                self.frame_queue.put(frame, block=False)
            except queue.Full:
                pass
            
            self.frame_count += 1
            
            # Throttle capture rate if needed
            if self.config['system']['limit_fps']:
                time.sleep(1.0 / self.config['system']['target_fps'])

    def process_frames(self):
        """Thread function to process frames with YOLOv8 model"""
        while self.running:
            try:
                frame = self.frame_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            
            self.perf_monitor.start_process_timer()
            
            # Run YOLOv8 detection
            results = self.model(
                frame, 
                conf=self.conf_threshold, 
                classes=self.target_classes, 
                verbose=False
            )
            
            # Process the results
            processed_frame, detections = self.process_results(frame, results[0])
            
            self.perf_monitor.stop_process_timer()
            
            # Put results in the output queue
            try:
                self.result_queue.put((processed_frame, detections), block=False)
            except queue.Full:
                pass

    def process_results(self, frame, results):
        """Process detection results and check for intrusions"""
        detections = []
        
        # Get detection boxes, convert to expected format
        if results.boxes is not None and len(results.boxes) > 0:
            boxes = results.boxes.cpu().numpy()
            
            for i, box in enumerate(boxes):
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                
                # Only process target classes
                if cls_id in self.target_classes:
                    # Calculate bottom center point (feet position)
                    feet_x = (x1 + x2) // 2
                    feet_y = y2
                    
                    # Check if this point is in any detection zone
                    detection_point = Point(feet_x, feet_y)
                    zone_id = self.zone_manager.check_point_in_zones(detection_point)
                    
                    if zone_id:
                        # We have an intrusion!
                        detections.append({
                            'bbox': (x1, y1, x2, y2),
                            'confidence': conf,
                            'class_id': cls_id, 
                            'class_name': results.names[cls_id],
                            'zone_id': zone_id,
                            'timestamp': datetime.now().isoformat()
                        })
                        
                        # Draw red box for intrusions
                        color = (0, 0, 255)  # Red for intrusion
                        thickness = 2
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
                        
                        # Add label with class name and confidence
                        label = f"{results.names[cls_id]}: {conf:.2f} - INTRUSION in {zone_id}"
                        cv2.putText(
                            frame, label, (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2
                        )
                        
                        # Mark the feet point
                        cv2.circle(frame, (feet_x, feet_y), 5, (0, 255, 255), -1)
                    else:
                        # Draw green box for non-intrusions
                        color = (0, 255, 0)  # Green for non-intrusion
                        thickness = 2
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
                        
                        # Add label with class name and confidence
                        label = f"{results.names[cls_id]}: {conf:.2f}"
                        cv2.putText(
                            frame, label, (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2
                        )
        
        # Draw zones on the frame
        frame = self.zone_manager.draw_zones(frame)
        
        # Add performance metrics to the frame
        fps = self.perf_monitor.get_fps()
        cv2.putText(
            frame, f"FPS: {fps:.1f}", (10, 30), 
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2
        )
        
        return frame, detections

    def handle_output(self):
        """Thread function to handle output frames and send alerts"""
        while self.running:
            try:
                frame, detections = self.result_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            
            # Check if we need to send alerts
            if detections and self._should_send_alert():
                self.alert_manager.send_alert(frame, detections)
                self.last_alert_time = time.time()
                logger.info(f"Alert sent for {len(detections)} intrusions")
            
            # Display the frame if enabled
            if self.config['output']['display_video']:
                cv2.imshow('Intruder Detection', frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    self.running = False
                    break
            
            # Save the frame if enabled
            if self.config['output']['save_video'] and self.output_video is not None:
                self.output_video.write(frame)
            
            # Save detection frames at configured interval
            if (self.config['output']['save_detection_frames'] and 
                detections and 
                self.frame_count - self.last_saved_frame >= self.config['output']['frame_save_interval']):
                self._save_detection_frame(frame, detections)
                self.last_saved_frame = self.frame_count
            
            # Log detections
            for detection in detections:
                logger.info(
                    f"Intrusion detected: {detection['class_name']} in zone {detection['zone_id']} "
                    f"with confidence {detection['confidence']:.2f}"
                )

    def _should_send_alert(self):
        """Check if we should send an alert based on cooldown time"""
        cooldown = self.config['alerts']['cooldown_seconds']
        return time.time() - self.last_alert_time > cooldown

    def _save_detection_frame(self, frame, detections):
        """Save detection frame to disk"""
        output_dir = Path(self.config['output']['detection_frames_dir'])
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"intrusion_{timestamp}.jpg"
        
        cv2.imwrite(str(output_path), frame)
        
        # Save detection metadata
        metadata_path = output_dir / f"intrusion_{timestamp}.json"
        with open(metadata_path, 'w') as f:
            json.dump(detections, f, indent=2)

    def run(self):
        """Run the intruder detection system"""
        self.running = True
        logger.info("Starting Intruder Detection System")
        
        # Start the threads
        capture_thread = Thread(target=self.capture_frames)
        process_thread = Thread(target=self.process_frames)
        output_thread = Thread(target=self.handle_output)
        
        capture_thread.start()
        process_thread.start()
        output_thread.start()
        
        try:
            # Wait for threads to finish
            capture_thread.join()
            process_thread.join()
            output_thread.join()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
            self.running = False
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up resources...")
        
        if self.cap is not None:
            self.cap.release()
        
        if self.output_video is not None:
            self.output_video.release()
        
        cv2.destroyAllWindows()
        
        # Print performance summary
        logger.info("\n" + self.perf_monitor.get_summary())
        logger.info("Intruder Detection System shut down successfully")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Intruder Detection System')
    parser.add_argument('--config', type=str, default='config/config.json',
                        help='Path to configuration file')
    parser.add_argument('--benchmark', action='store_true',
                        help='Run in benchmark mode to measure performance')
    parser.add_argument('--low-power', action='store_true',
                        help='Run in low-power mode to save energy')
    return parser.parse_args()

def main():
    """Main function"""
    args = parse_arguments()
    
    # Apply low-power mode if requested
    if args.low_power:
        os.system("sudo nvpmodel -m 1")  # Set Jetson Nano to 5W mode
        os.system("sudo jetson_clocks --store")
        os.system("sudo jetson_clocks --fan")
        print("Low-power mode enabled (5W)")
    
    # Initialize and run the system
    system = IntruderDetectionSystem(config_path=args.config)
    
    # Run benchmarking if requested
    if args.benchmark:
        from utils.benchmarking import run_benchmark
        run_benchmark(system)
    else:
        system.run()
    
    # Restore power settings if modified
    if args.low_power:
        os.system("sudo jetson_clocks --restore")
        print("Power settings restored")

if __name__ == "__main__":
    main() 