#!/usr/bin/env python3
"""
Alert Manager for Intruder Detection System
Handles sending alerts via email and Telegram
"""

import os
import cv2
import json
import time
import logging
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime
from threading import Thread, Lock
import numpy as np

logger = logging.getLogger('AlertManager')

class AlertManager:
    def __init__(self, alerts_config):
        """Initialize the alert manager with alert configurations
        
        Args:
            alerts_config (dict): Dictionary of alert configurations
        """
        self.config = alerts_config
        self.enabled = alerts_config.get('enabled', True)
        self.cooldown_seconds = alerts_config.get('cooldown_seconds', 60)
        self.last_alert_time = 0
        self.alert_lock = Lock()
        
        # Email configuration
        self.email_enabled = alerts_config.get('email', {}).get('enabled', False)
        self.email_config = alerts_config.get('email', {})
        
        # Telegram configuration
        self.telegram_enabled = alerts_config.get('telegram', {}).get('enabled', False)
        self.telegram_config = alerts_config.get('telegram', {})
        
        # Alert history
        self.alerts_dir = Path(alerts_config.get('history_dir', 'logs/alerts'))
        self.alerts_dir.mkdir(exist_ok=True, parents=True)
        
        logger.info("Alert Manager initialized")
        
        # Check and log enabled alert methods
        enabled_methods = []
        if self.email_enabled:
            enabled_methods.append("Email")
        if self.telegram_enabled:
            enabled_methods.append("Telegram")
            
        if enabled_methods:
            logger.info(f"Enabled alert methods: {', '.join(enabled_methods)}")
        else:
            logger.warning("No alert methods enabled!")
    
    def send_alert(self, frame, detections):
        """Send alerts through all enabled channels
        
        Args:
            frame (numpy.ndarray): The frame with detections
            detections (list): List of detection dictionaries
        
        Returns:
            bool: True if alerts were sent successfully
        """
        if not self.enabled:
            return False
            
        # Use lock to prevent multiple simultaneous alerts
        with self.alert_lock:
            current_time = time.time()
            if current_time - self.last_alert_time < self.cooldown_seconds:
                logger.debug("Alert cooldown active, skipping")
                return False
                
            self.last_alert_time = current_time
            
            # Save the alert image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            alert_img_path = self.alerts_dir / f"alert_{timestamp}.jpg"
            cv2.imwrite(str(alert_img_path), frame)
            
            # Save detection metadata
            alert_meta_path = self.alerts_dir / f"alert_{timestamp}.json"
            with open(alert_meta_path, 'w') as f:
                json.dump(detections, f, indent=2)
            
            success = True
            
            # Send alerts in separate threads to avoid blocking
            if self.email_enabled:
                email_thread = Thread(
                    target=self._send_email_alert,
                    args=(str(alert_img_path), detections)
                )
                email_thread.start()
            
            if self.telegram_enabled:
                telegram_thread = Thread(
                    target=self._send_telegram_alert,
                    args=(str(alert_img_path), detections)
                )
                telegram_thread.start()
            
            return success
    
    def _send_email_alert(self, image_path, detections):
        """Send an email alert with the detection image
        
        Args:
            image_path (str): Path to the detection image
            detections (list): List of detection dictionaries
        """
        try:
            # Create the email
            msg = MIMEMultipart()
            msg['Subject'] = self.email_config.get('subject', 'Intruder Alert!')
            msg['From'] = self.email_config.get('from_email')
            msg['To'] = self.email_config.get('to_email')
            
            # Create the message body with detection details
            detection_text = []
            for i, detection in enumerate(detections):
                detection_text.append(
                    f"Detection {i+1}: {detection['class_name']} in zone {detection['zone_id']} "
                    f"(confidence: {detection['confidence']:.2f})"
                )
            
            alert_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            body_text = (
                f"Intruder Detection Alert\n"
                f"Time: {alert_time}\n"
                f"Number of detections: {len(detections)}\n\n"
                f"{chr(10).join(detection_text)}"
            )
            
            msg.attach(MIMEText(body_text))
            
            # Attach the image
            with open(image_path, 'rb') as f:
                img_data = f.read()
                image = MIMEImage(img_data, name=os.path.basename(image_path))
                msg.attach(image)
            
            # Connect to SMTP server and send email
            with smtplib.SMTP(
                self.email_config.get('smtp_server'), 
                self.email_config.get('smtp_port', 587)
            ) as smtp:
                smtp.starttls()
                smtp.login(
                    self.email_config.get('username'),
                    self.email_config.get('password')
                )
                smtp.send_message(msg)
            
            logger.info("Email alert sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False
    
    def _send_telegram_alert(self, image_path, detections):
        """Send a Telegram alert with the detection image
        
        Args:
            image_path (str): Path to the detection image
            detections (list): List of detection dictionaries
        """
        try:
            bot_token = self.telegram_config.get('bot_token')
            chat_id = self.telegram_config.get('chat_id')
            
            if not bot_token or not chat_id:
                logger.error("Telegram bot token or chat ID not configured")
                return False
            
            # Create caption with detection details
            detection_text = []
            for i, detection in enumerate(detections):
                detection_text.append(
                    f"Detection {i+1}: {detection['class_name']} in zone {detection['zone_id']} "
                    f"(confidence: {detection['confidence']:.2f})"
                )
            
            alert_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            caption = (
                f"🚨 *INTRUDER ALERT* 🚨\n"
                f"Time: {alert_time}\n"
                f"Detections: {len(detections)}\n\n"
                f"{chr(10).join(detection_text)}"
            )
            
            # Send photo with caption
            url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
            files = {'photo': open(image_path, 'rb')}
            data = {'chat_id': chat_id, 'caption': caption, 'parse_mode': 'Markdown'}
            
            response = requests.post(url, files=files, data=data)
            response.raise_for_status()
            
            logger.info("Telegram alert sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
            return False
    
    def test_alerts(self):
        """Test all configured alert methods with a test message
        
        Returns:
            dict: Dictionary with test results for each method
        """
        results = {'email': False, 'telegram': False}
        test_image = np.zeros((300, 400, 3), dtype=np.uint8)
        
        # Add text to test image
        cv2.putText(
            test_image, "TEST ALERT", (50, 150), 
            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2
        )
        
        # Save test image
        test_img_path = self.alerts_dir / "test_alert.jpg"
        cv2.imwrite(str(test_img_path), test_image)
        
        # Test email
        if self.email_enabled:
            results['email'] = self._send_email_alert(
                str(test_img_path),
                [{'class_name': 'person', 'zone_id': 'test_zone', 'confidence': 0.95}]
            )
        
        # Test Telegram
        if self.telegram_enabled:
            results['telegram'] = self._send_telegram_alert(
                str(test_img_path),
                [{'class_name': 'person', 'zone_id': 'test_zone', 'confidence': 0.95}]
            )
        
        return results 