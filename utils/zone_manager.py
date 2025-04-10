#!/usr/bin/env python3
"""
Zone Manager for Intruder Detection System
Handles zone definitions and intrusion detection logic
"""

import cv2
import numpy as np
from shapely.geometry import Point, Polygon


class ZoneManager:
    def __init__(self, zones_config):
        """Initialize the zone manager with zone configurations
        
        Args:
            zones_config (dict): Dictionary of zone configurations
                Each zone should have:
                - name: Zone name/identifier
                - points: List of (x,y) coordinates defining the polygon
                - color: (B,G,R) color for visualization
        """
        self.zones = {}
        self.load_zones(zones_config)
    
    def load_zones(self, zones_config):
        """Load zones from configuration
        
        Args:
            zones_config (dict): Dictionary of zone configurations
        """
        for zone_id, zone_data in zones_config.items():
            # Create shapely polygon for the zone
            points = zone_data.get('points', [])
            if len(points) < 3:
                continue  # Skip invalid zones (need at least 3 points)
            
            polygon = Polygon(points)
            color = zone_data.get('color', (0, 0, 255))  # Default is red
            
            # Store zone data
            self.zones[zone_id] = {
                'name': zone_data.get('name', zone_id),
                'polygon': polygon,
                'points': points,
                'color': color,
                'alert_enabled': zone_data.get('alert_enabled', True)
            }
    
    def check_point_in_zones(self, point):
        """Check if a point is inside any of the defined zones
        
        Args:
            point (Point): Shapely Point object to check
        
        Returns:
            str: Zone ID if the point is in a zone, None otherwise
        """
        for zone_id, zone_data in self.zones.items():
            # Skip zones with alerts disabled
            if not zone_data.get('alert_enabled', True):
                continue
                
            # Check if point is inside the polygon
            if zone_data['polygon'].contains(point):
                return zone_id
        
        return None
    
    def draw_zones(self, frame):
        """Draw all zones on the frame
        
        Args:
            frame (numpy.ndarray): Frame to draw on
        
        Returns:
            numpy.ndarray: Frame with zones drawn
        """
        for zone_id, zone_data in self.zones.items():
            points = np.array(zone_data['points'], np.int32)
            points = points.reshape((-1, 1, 2))
            
            # Draw filled polygon with transparency
            overlay = frame.copy()
            cv2.fillPoly(overlay, [points], zone_data['color'])
            alpha = 0.3  # Transparency factor
            cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
            
            # Draw polygon outline
            cv2.polylines(frame, [points], True, zone_data['color'], 2)
            
            # Add zone name
            centroid = zone_data['polygon'].centroid
            cx, cy = int(centroid.x), int(centroid.y)
            cv2.putText(
                frame, zone_data['name'], (cx, cy), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2
            )
        
        return frame
    
    def update_zone(self, zone_id, points=None, alert_enabled=None, color=None):
        """Update an existing zone
        
        Args:
            zone_id (str): ID of the zone to update
            points (list, optional): New points for the zone
            alert_enabled (bool, optional): Whether alerts are enabled
            color (tuple, optional): New color for the zone
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        if zone_id not in self.zones:
            return False
            
        if points is not None and len(points) >= 3:
            self.zones[zone_id]['points'] = points
            self.zones[zone_id]['polygon'] = Polygon(points)
            
        if alert_enabled is not None:
            self.zones[zone_id]['alert_enabled'] = alert_enabled
            
        if color is not None:
            self.zones[zone_id]['color'] = color
            
        return True
        
    def add_zone(self, zone_id, name, points, color=(0, 0, 255), alert_enabled=True):
        """Add a new zone
        
        Args:
            zone_id (str): ID for the new zone
            name (str): Name for the zone
            points (list): List of (x,y) coordinates
            color (tuple, optional): (B,G,R) color
            alert_enabled (bool, optional): Whether alerts are enabled
            
        Returns:
            bool: True if addition was successful, False otherwise
        """
        if zone_id in self.zones or len(points) < 3:
            return False
            
        polygon = Polygon(points)
        self.zones[zone_id] = {
            'name': name,
            'polygon': polygon,
            'points': points,
            'color': color,
            'alert_enabled': alert_enabled
        }
        
        return True
        
    def remove_zone(self, zone_id):
        """Remove a zone
        
        Args:
            zone_id (str): ID of the zone to remove
            
        Returns:
            bool: True if removal was successful, False otherwise
        """
        if zone_id not in self.zones:
            return False
            
        del self.zones[zone_id]
        return True 