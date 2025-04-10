#!/usr/bin/env python3
"""
Performance Monitor for Intruder Detection System
Tracks and reports system performance metrics
"""

import time
import logging
import numpy as np
from collections import deque

logger = logging.getLogger('PerformanceMonitor')

class PerformanceMonitor:
    def __init__(self, max_samples=100):
        """Initialize the performance monitor
        
        Args:
            max_samples (int): Maximum number of timing samples to keep
        """
        # FPS tracking
        self.fps_samples = deque(maxlen=max_samples)
        self.last_frame_time = time.time()
        
        # Processing timing
        self.process_times = deque(maxlen=max_samples)
        self.process_start_time = None
        
        # Memory tracking (if available)
        self.memory_samples = deque(maxlen=max_samples)
        self.track_memory = False
        
        try:
            import psutil
            self.psutil = psutil
            self.track_memory = True
        except ImportError:
            logger.info("psutil not available, memory tracking disabled")
            self.psutil = None
        
        # CPU temperature (for Jetson devices)
        self.temperature_samples = deque(maxlen=max_samples)
        self.track_temperature = False
        
        try:
            # Check if we're on a Jetson device
            with open("/sys/devices/virtual/thermal/thermal_zone0/temp", "r") as f:
                self.track_temperature = True
        except (FileNotFoundError, PermissionError):
            logger.info("Temperature monitoring not available")
        
        logger.info("Performance Monitor initialized")
    
    def update_fps(self):
        """Update FPS calculation based on time between frames"""
        current_time = time.time()
        elapsed = current_time - self.last_frame_time
        self.last_frame_time = current_time
        
        if elapsed > 0:
            fps = 1.0 / elapsed
            self.fps_samples.append(fps)
    
    def start_process_timer(self):
        """Start timing the processing of a frame"""
        self.process_start_time = time.time()
    
    def stop_process_timer(self):
        """Stop timing the processing of a frame and record the duration"""
        if self.process_start_time is not None:
            elapsed = time.time() - self.process_start_time
            self.process_times.append(elapsed)
            self.process_start_time = None
            
            # Also update FPS
            self.update_fps()
            
            # Update memory if tracking is enabled
            if self.track_memory and self.psutil is not None:
                process = self.psutil.Process()
                memory_info = process.memory_info()
                self.memory_samples.append(memory_info.rss / 1024 / 1024)  # MB
                
            # Update temperature if tracking is enabled
            if self.track_temperature:
                try:
                    with open("/sys/devices/virtual/thermal/thermal_zone0/temp", "r") as f:
                        temp = float(f.read().strip()) / 1000  # Convert to degrees C
                        self.temperature_samples.append(temp)
                except (FileNotFoundError, PermissionError, ValueError):
                    pass
    
    def get_fps(self):
        """Get the current FPS (averaged over recent samples)
        
        Returns:
            float: Current FPS
        """
        if not self.fps_samples:
            return 0.0
        
        return np.mean(self.fps_samples)
    
    def get_process_time(self):
        """Get the average frame processing time in milliseconds
        
        Returns:
            float: Average processing time in milliseconds
        """
        if not self.process_times:
            return 0.0
        
        return np.mean(self.process_times) * 1000  # Convert to ms
    
    def get_memory_usage(self):
        """Get the current memory usage in MB
        
        Returns:
            float: Memory usage in MB or 0 if not available
        """
        if not self.memory_samples or not self.track_memory:
            return 0.0
        
        return np.mean(self.memory_samples)
    
    def get_temperature(self):
        """Get the current CPU temperature in degrees C
        
        Returns:
            float: CPU temperature or 0 if not available
        """
        if not self.temperature_samples or not self.track_temperature:
            return 0.0
        
        return np.mean(self.temperature_samples)
    
    def get_summary(self):
        """Get a summary of all performance metrics
        
        Returns:
            str: Formatted summary string
        """
        summary = [
            "Performance Summary:",
            f"FPS: {self.get_fps():.2f}",
            f"Process Time: {self.get_process_time():.2f} ms",
        ]
        
        if self.track_memory:
            summary.append(f"Memory Usage: {self.get_memory_usage():.2f} MB")
        
        if self.track_temperature:
            summary.append(f"CPU Temperature: {self.get_temperature():.2f}°C")
        
        return "\n".join(summary)
    
    def reset(self):
        """Reset all performance metrics"""
        self.fps_samples.clear()
        self.process_times.clear()
        self.memory_samples.clear()
        self.temperature_samples.clear()
        self.last_frame_time = time.time()
        self.process_start_time = None 