#!/usr/bin/env python3
"""
Configuration Loader for Intruder Detection System
Loads and validates system configuration from JSON files
"""

import os
import json
import logging
from pathlib import Path

logger = logging.getLogger('ConfigLoader')

class ConfigLoader:
    def __init__(self, config_path):
        """Initialize the configuration loader
        
        Args:
            config_path (str): Path to the configuration file
        """
        self.config_path = config_path
        self.config = {}
        
    def load_config(self):
        """Load configuration from file and apply defaults
        
        Returns:
            dict: Configuration dictionary
        """
        try:
            # Ensure the config directory exists
            config_dir = os.path.dirname(self.config_path)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir)
            
            # Load config if it exists, otherwise create default
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
                logger.info(f"Loaded configuration from {self.config_path}")
            else:
                logger.warning(f"Configuration file {self.config_path} not found, creating default")
                self.config = self._create_default_config()
                self._save_config()
                
            # Validate and fill in missing values
            self._validate_config()
            
            return self.config
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            logger.info("Using default configuration")
            self.config = self._create_default_config()
            return self.config
    
    def _create_default_config(self):
        """Create a default configuration
        
        Returns:
            dict: Default configuration dictionary
        """
        return {
            # Model configuration
            "model": {
                "path": "yolov8n.pt",
                "confidence_threshold": 0.5,
                "use_tensorrt": True,
                "target_classes": [0]  # Person class by default
            },
            
            # Camera configuration
            "camera": {
                "source": "0",  # USB camera
                "width": 640,
                "height": 480
            },
            
            # System configuration
            "system": {
                "queue_size": 10,
                "limit_fps": True,
                "target_fps": 15,
                "reconnect_on_failure": True
            },
            
            # Zones configuration
            "zones": {
                "zone1": {
                    "name": "Main Entrance",
                    "points": [[100, 400], [300, 400], [300, 300], [100, 300]],
                    "color": [0, 0, 255],
                    "alert_enabled": True
                },
                "zone2": {
                    "name": "Side Door",
                    "points": [[400, 400], [600, 400], [600, 300], [400, 300]],
                    "color": [0, 255, 0],
                    "alert_enabled": True
                }
            },
            
            # Alert configuration
            "alerts": {
                "enabled": True,
                "cooldown_seconds": 60,
                "history_dir": "logs/alerts",
                
                # Email alerts
                "email": {
                    "enabled": False,
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "username": "your-email@gmail.com",
                    "password": "your-app-password",
                    "from_email": "your-email@gmail.com",
                    "to_email": "recipient@example.com",
                    "subject": "Intruder Alert!"
                },
                
                # Telegram alerts
                "telegram": {
                    "enabled": False,
                    "bot_token": "your-bot-token",
                    "chat_id": "your-chat-id"
                }
            },
            
            # Output configuration
            "output": {
                "display_video": True,
                "save_video": True,
                "output_dir": "data/recordings",
                "output_fps": 10,
                "save_detection_frames": True,
                "detection_frames_dir": "data/detections",
                "frame_save_interval": 15  # Save every 15th detection frame
            }
        }
    
    def _validate_config(self):
        """Validate configuration and apply defaults for missing values"""
        # Ensure basic sections exist
        required_sections = ["model", "camera", "system", "zones", "alerts", "output"]
        for section in required_sections:
            if section not in self.config:
                self.config[section] = self._create_default_config()[section]
                logger.warning(f"Missing {section} configuration, using defaults")
        
        # Validate model configuration
        if not os.path.exists(self.config["model"]["path"]):
            logger.warning(f"Model file {self.config['model']['path']} not found")
            
        # Ensure target_classes is a list
        if not isinstance(self.config["model"].get("target_classes", []), list):
            self.config["model"]["target_classes"] = [0]  # Default to person class
            
        # Create required directories
        self._create_directories()
        
    def _create_directories(self):
        """Create required directories from configuration"""
        directories = [
            os.path.dirname(self.config_path),
            self.config["output"]["output_dir"],
            self.config["output"]["detection_frames_dir"],
            self.config["alerts"]["history_dir"],
            "logs"
        ]
        
        for directory in directories:
            if directory:
                os.makedirs(directory, exist_ok=True)
                
    def _save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Saved configuration to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            
    def update_config(self, updates):
        """Update configuration with new values and save
        
        Args:
            updates (dict): Dictionary of updates to apply
            
        Returns:
            dict: Updated configuration
        """
        def update_nested_dict(d, u):
            for k, v in u.items():
                if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                    update_nested_dict(d[k], v)
                else:
                    d[k] = v
        
        update_nested_dict(self.config, updates)
        self._save_config()
        return self.config 