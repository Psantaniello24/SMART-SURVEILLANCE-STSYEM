#!/usr/bin/env python3
"""
Zone Configuration Utility for Smart Surveillance System
This script allows users to visually define intrusion detection zones
"""

import os
import sys
import cv2
import json
import argparse
import logging
import numpy as np
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import utilities
try:
    from utils.config_loader import ConfigLoader
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
logger = logging.getLogger('ZoneConfig')

class ZoneConfigurationTool:
    def __init__(self, config_path="config/config.json", camera_source=None):
        """Initialize Zone Configuration Tool
        
        Args:
            config_path (str): Path to configuration file
            camera_source (str, optional): Override camera source from config
        """
        self.config_loader = ConfigLoader(config_path)
        self.config = self.config_loader.load_config()
        
        # Override camera source if provided
        if camera_source is not None:
            self.config["camera"]["source"] = camera_source
        
        self.source = self.config["camera"]["source"]
        self.current_zone = None
        self.drawing = False
        self.points = []
        self.zones = self.config["zones"].copy()
        self.colors = {
            "red": (0, 0, 255),
            "green": (0, 255, 0),
            "blue": (255, 0, 0),
            "yellow": (0, 255, 255),
            "purple": (255, 0, 255),
            "cyan": (255, 255, 0),
            "white": (255, 255, 255)
        }
        
        # Drawing settings
        self.frame = None
        self.temp_point = None
        self.saved_frame = None
        self.help_displayed = False
        
    def setup_camera(self):
        """Initialize the camera"""
        source = self.source
        
        # Try to convert to integer for USB camera indices
        try:
            source = int(source)
        except ValueError:
            pass
            
        self.cap = cv2.VideoCapture(source)
        
        if not self.cap.isOpened():
            logger.error(f"Failed to open camera: {source}")
            sys.exit(1)
            
        # Set camera properties if specified
        if 'width' in self.config['camera'] and 'height' in self.config['camera']:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config['camera']['width'])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config['camera']['height'])
            
        # Get actual frame dimensions
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        logger.info(f"Camera initialized with resolution: {self.frame_width}x{self.frame_height}")
        
    def mouse_callback(self, event, x, y, flags, param):
        """Mouse callback for zone drawing"""
        if event == cv2.EVENT_LBUTTONDOWN:
            # Start drawing a new zone or add point to current zone
            if not self.drawing:
                self.start_new_zone(x, y)
            else:
                self.add_point(x, y)
        elif event == cv2.EVENT_MOUSEMOVE:
            # Update temporary point while moving mouse
            self.temp_point = (x, y)
        elif event == cv2.EVENT_RBUTTONDOWN:
            # Finish the current zone
            self.finish_zone()
            
    def start_new_zone(self, x, y):
        """Start a new zone with the first point"""
        if self.drawing:
            self.finish_zone()
            
        # Ask for zone name
        cv2.putText(
            self.frame, "Enter zone name in terminal", (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2
        )
        cv2.imshow("Zone Configuration", self.frame)
        
        zone_name = input("Enter zone name: ")
        zone_id = zone_name.lower().replace(" ", "_")
        
        # If zone already exists, ask if should override
        if zone_id in self.zones:
            override = input(f"Zone '{zone_id}' already exists. Override? (y/n): ")
            if override.lower() != 'y':
                print("Zone creation cancelled.")
                return
        
        # Ask for zone color
        print("Available colors:", ", ".join(self.colors.keys()))
        color_name = input(f"Enter zone color ({', '.join(self.colors.keys())}): ")
        color = self.colors.get(color_name.lower(), (0, 0, 255))  # Default to red
        
        self.current_zone = {
            "name": zone_name,
            "points": [(x, y)],
            "color": color,
            "alert_enabled": True
        }
        
        self.drawing = True
        self.points = [(x, y)]
        print(f"Started new zone: {zone_name}")
        print("Left-click to add points, right-click to finish zone")
        
    def add_point(self, x, y):
        """Add a point to the current zone"""
        if self.drawing and self.current_zone:
            self.points.append((x, y))
            self.current_zone["points"].append((x, y))
            
    def finish_zone(self):
        """Finish drawing the current zone"""
        if self.drawing and self.current_zone and len(self.points) >= 3:
            zone_id = self.current_zone["name"].lower().replace(" ", "_")
            self.zones[zone_id] = self.current_zone
            print(f"Finished zone: {self.current_zone['name']} with {len(self.points)} points")
            
            # Save zones to config
            self.save_zones()
        elif self.drawing and len(self.points) < 3:
            print("Cannot create zone with fewer than 3 points. Zone discarded.")
            
        self.drawing = False
        self.current_zone = None
        self.points = []
        self.temp_point = None
        
    def delete_zone(self, zone_id):
        """Delete a zone"""
        if zone_id in self.zones:
            print(f"Deleting zone: {self.zones[zone_id]['name']}")
            del self.zones[zone_id]
            self.save_zones()
        else:
            print(f"Zone '{zone_id}' not found.")
            
    def save_zones(self):
        """Save zones to configuration file"""
        self.config["zones"] = self.zones
        self.config_loader.update_config({"zones": self.zones})
        print(f"Saved {len(self.zones)} zones to configuration")
        
    def draw_zones(self, frame):
        """Draw all zones on the frame"""
        for zone_id, zone_data in self.zones.items():
            points = np.array(zone_data["points"], np.int32)
            points = points.reshape((-1, 1, 2))
            
            # Draw filled polygon with transparency
            overlay = frame.copy()
            cv2.fillPoly(overlay, [points], zone_data["color"])
            alpha = 0.3  # Transparency factor
            cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
            
            # Draw polygon outline
            cv2.polylines(frame, [points], True, zone_data["color"], 2)
            
            # Add zone name
            cx = sum(p[0] for p in zone_data["points"]) // len(zone_data["points"])
            cy = sum(p[1] for p in zone_data["points"]) // len(zone_data["points"])
            cv2.putText(
                frame, zone_data["name"], (cx, cy),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2
            )
            
        return frame
        
    def draw_current_zone(self, frame):
        """Draw the zone currently being created"""
        if self.drawing and self.points:
            # Draw the existing lines
            for i in range(len(self.points) - 1):
                cv2.line(
                    frame, self.points[i], self.points[i + 1],
                    self.current_zone["color"], 2
                )
                
            # Draw temporary line from last point to mouse position
            if self.temp_point:
                cv2.line(
                    frame, self.points[-1], self.temp_point,
                    self.current_zone["color"], 2
                )
                
            # Draw points
            for point in self.points:
                cv2.circle(frame, point, 5, (0, 255, 255), -1)
                
        return frame
        
    def draw_help(self, frame):
        """Draw help text on the frame"""
        if self.help_displayed:
            help_text = [
                "Controls:",
                "Left click: Add point",
                "Right click: Finish zone",
                "S: Save frame",
                "F: Freeze/unfreeze frame",
                "D: Delete zone (prompt will appear)",
                "H: Toggle this help",
                "ESC/Q: Quit"
            ]
            
            y = 40
            for text in help_text:
                cv2.putText(
                    frame, text, (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2
                )
                y += 25
                
        else:
            cv2.putText(
                frame, "Press 'H' for help", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2
            )
            
        return frame
        
    def run(self):
        """Run the zone configuration tool"""
        self.setup_camera()
        
        # Create window and set mouse callback
        cv2.namedWindow("Zone Configuration")
        cv2.setMouseCallback("Zone Configuration", self.mouse_callback)
        
        frozen = False
        
        while True:
            if not frozen or self.frame is None:
                ret, self.frame = self.cap.read()
                if not ret:
                    logger.error("Failed to capture frame")
                    break
            
            # Draw existing zones
            self.draw_zones(self.frame)
            
            # Draw current zone being created
            self.draw_current_zone(self.frame)
            
            # Draw help text
            self.draw_help(self.frame)
            
            # Show frame
            cv2.imshow("Zone Configuration", self.frame)
            
            key = cv2.waitKey(1) & 0xFF
            
            # Process key presses
            if key == 27 or key == ord('q'):  # ESC or Q
                break
            elif key == ord('s'):  # Save frame
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"zone_config_{timestamp}.jpg"
                cv2.imwrite(filename, self.frame)
                print(f"Saved frame to {filename}")
            elif key == ord('f'):  # Freeze/unfreeze frame
                frozen = not frozen
                print("Frame " + ("frozen" if frozen else "unfrozen"))
            elif key == ord('d'):  # Delete zone
                print("Available zones:", ", ".join(self.zones.keys()))
                zone_id = input("Enter zone ID to delete: ")
                self.delete_zone(zone_id)
            elif key == ord('h'):  # Toggle help
                self.help_displayed = not self.help_displayed
                
        # Clean up
        self.cap.release()
        cv2.destroyAllWindows()
        
def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Zone Configuration Tool')
    parser.add_argument('--config', type=str, default='config/config.json',
                     help='Path to configuration file')
    parser.add_argument('--camera', type=str, default=None,
                     help='Camera source (overrides config)')
    args = parser.parse_args()
    
    tool = ZoneConfigurationTool(args.config, args.camera)
    tool.run()
    
if __name__ == "__main__":
    import time  # Import needed for timestamp
    main() 