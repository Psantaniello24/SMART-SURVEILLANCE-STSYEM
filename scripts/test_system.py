#!/usr/bin/env python3
"""
Test Script for Smart Surveillance System
Tests various components to verify proper installation and functionality
"""

import os
import sys
import time
import logging
import json
import argparse

# Add parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import system components
try:
    from utils.config_loader import ConfigLoader
    from utils.alert_manager import AlertManager
    from utils.zone_manager import ZoneManager
    from utils.performance_monitor import PerformanceMonitor
except ImportError as e:
    print(f"Error importing system components: {e}")
    print("Make sure you're running this script from the project root directory.")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('TestSystem')

def test_config_loader():
    """Test the ConfigLoader class"""
    logger.info("Testing ConfigLoader...")
    
    # Create a test config
    test_config_path = "config/test_config.json"
    
    # Create config loader
    config_loader = ConfigLoader(test_config_path)
    
    # Load the config (this will create a default config if it doesn't exist)
    config = config_loader.load_config()
    
    # Verify essential sections
    required_sections = ["model", "camera", "system", "zones", "alerts", "output"]
    for section in required_sections:
        assert section in config, f"Missing section: {section}"
    
    logger.info("ConfigLoader test passed ✓")
    
    # Clean up
    if os.path.exists(test_config_path):
        os.remove(test_config_path)
    
    return config

def test_zone_manager(config):
    """Test the ZoneManager class"""
    logger.info("Testing ZoneManager...")
    
    # Create zone manager
    zone_manager = ZoneManager(config["zones"])
    
    # Test zone detection
    test_zone = list(config["zones"].keys())[0]
    test_zone_data = config["zones"][test_zone]
    
    # Get a point inside the zone (center of the polygon)
    points = test_zone_data["points"]
    center_x = sum(p[0] for p in points) // len(points)
    center_y = sum(p[1] for p in points) // len(points)
    
    # Create test point
    from shapely.geometry import Point
    test_point = Point(center_x, center_y)
    
    # Test if the point is in the zone
    detected_zone = zone_manager.check_point_in_zones(test_point)
    assert detected_zone == test_zone, f"Expected zone {test_zone}, got {detected_zone}"
    
    # Test zone operations
    new_zone_id = "test_zone"
    assert zone_manager.add_zone(
        new_zone_id, 
        "Test Zone", 
        [[10, 10], [10, 100], [100, 100], [100, 10]]
    ), "Failed to add new zone"
    
    assert zone_manager.update_zone(
        new_zone_id, 
        points=[[20, 20], [20, 200], [200, 200], [200, 20]]
    ), "Failed to update zone"
    
    assert zone_manager.remove_zone(new_zone_id), "Failed to remove zone"
    
    logger.info("ZoneManager test passed ✓")

def test_alert_manager(config):
    """Test the AlertManager class"""
    logger.info("Testing AlertManager...")
    
    # Create alert manager
    alert_manager = AlertManager(config["alerts"])
    
    # Test test_alerts method (don't actually send alerts)
    alert_manager.email_enabled = False
    alert_manager.telegram_enabled = False
    
    # This should run without errors but not actually send any alerts
    results = alert_manager.test_alerts()
    
    logger.info("AlertManager test passed ✓")

def test_performance_monitor():
    """Test the PerformanceMonitor class"""
    logger.info("Testing PerformanceMonitor...")
    
    # Create performance monitor
    perf_monitor = PerformanceMonitor()
    
    # Test timing functions
    perf_monitor.start_process_timer()
    time.sleep(0.1)  # Simulate processing
    perf_monitor.stop_process_timer()
    
    # Check that we recorded some time
    process_time = perf_monitor.get_process_time()
    assert process_time > 0, "Process time should be greater than 0"
    
    # Test FPS calculation
    fps = perf_monitor.get_fps()
    assert fps >= 0, "FPS should be greater than or equal to 0"
    
    # Test summary generation
    summary = perf_monitor.get_summary()
    assert "FPS:" in summary, "Summary should include FPS"
    assert "Process Time:" in summary, "Summary should include Process Time"
    
    logger.info("PerformanceMonitor test passed ✓")

def test_system_dependencies():
    """Test that system dependencies are installed and working"""
    logger.info("Testing system dependencies...")
    
    # Test OpenCV
    try:
        import cv2
        logger.info(f"OpenCV installed: {cv2.__version__}")
    except ImportError:
        logger.error("OpenCV (cv2) not installed")
        return False
    
    # Test numpy
    try:
        import numpy as np
        logger.info(f"NumPy installed: {np.__version__}")
    except ImportError:
        logger.error("NumPy not installed")
        return False
    
    # Test YOLOv8 (ultralytics)
    try:
        import ultralytics
        logger.info(f"Ultralytics installed: {ultralytics.__version__}")
    except ImportError:
        logger.error("Ultralytics (YOLOv8) not installed")
        return False
    
    # Test Shapely
    try:
        import shapely
        logger.info(f"Shapely installed: {shapely.__version__}")
    except ImportError:
        logger.error("Shapely not installed")
        return False
    
    # Test for TensorRT availability (optional)
    try:
        import tensorrt
        logger.info(f"TensorRT installed: {tensorrt.__version__}")
    except ImportError:
        logger.warning("TensorRT not installed - TensorRT optimization will not be available")
    
    logger.info("System dependencies test passed ✓")
    return True

def test_model_availability(config):
    """Test that the YOLOv8 model is available"""
    logger.info("Testing model availability...")
    
    model_path = config["model"]["path"]
    if not os.path.exists(model_path):
        logger.error(f"Model not found at: {model_path}")
        logger.info("You may need to download the model:")
        logger.info("wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt")
        return False
    
    logger.info(f"Model found at: {model_path}")
    
    # Try to load the model (if ultralytics is installed)
    try:
        from ultralytics import YOLO
        model = YOLO(model_path)
        logger.info(f"Successfully loaded model: {model_path}")
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        return False
    
    logger.info("Model availability test passed ✓")
    return True

def main():
    """Main test function"""
    parser = argparse.ArgumentParser(description='Test Smart Surveillance System')
    parser.add_argument('--config', type=str, default='config/config.json',
                        help='Path to configuration file')
    args = parser.parse_args()
    
    logger.info("Starting system tests...")
    
    # Check if config exists
    if not os.path.exists(args.config):
        logger.warning(f"Config file not found at: {args.config}")
        logger.info("Will create a default config for testing.")
    
    # Test config loader
    try:
        config = test_config_loader()
    except Exception as e:
        logger.error(f"ConfigLoader test failed: {e}")
        return False
    
    # Test system dependencies
    if not test_system_dependencies():
        logger.error("System dependencies test failed")
        return False
    
    # Test model availability
    if not test_model_availability(config):
        logger.error("Model availability test failed")
        return False
    
    # Test zone manager
    try:
        test_zone_manager(config)
    except Exception as e:
        logger.error(f"ZoneManager test failed: {e}")
        return False
    
    # Test alert manager
    try:
        test_alert_manager(config)
    except Exception as e:
        logger.error(f"AlertManager test failed: {e}")
        return False
    
    # Test performance monitor
    try:
        test_performance_monitor()
    except Exception as e:
        logger.error(f"PerformanceMonitor test failed: {e}")
        return False
    
    logger.info("All tests passed successfully! ✓")
    logger.info("The system should be ready to run.")
    logger.info("You can start the system with: python3 src/intruder_detection.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)