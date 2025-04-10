# Smart Surveillance System for Jetson Nano

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![CI Tests](https://github.com/username/smart-surveillance-system/actions/workflows/python-tests.yml/badge.svg)](https://github.com/username/smart-surveillance-system/actions/workflows/python-tests.yml)

A Python-based intruder detection system that leverages YOLOv8 with TensorRT optimization to efficiently process video streams on the NVIDIA Jetson Nano. The system includes zone-based intrusion detection, alerting mechanisms, and performance benchmarking.

## Video example :

![Demo GIF](./security_demo.gif)

## Features

- **YOLOv8 with TensorRT Optimization** - Fast object detection with hardware acceleration
- **High-performance Processing** - Optimized for 15+ FPS on Jetson Nano
- **Multiple Camera Sources** - Supports RTSP streams and USB cameras
- **Zone-based Intrusion Logic** - Define custom zones and detect intrusions
- **Alert System** - Configurable alerts via Email and Telegram
- **Performance Benchmarking** - Measure and optimize system performance
- **Low-power Mode** - Power-efficient operation for edge deployment
- **Output Options** - Real-time video display, recording, and timestamped logs



## System Requirements

- NVIDIA Jetson Nano (2GB or 4GB)
- JetPack 4.6 or later
- USB or CSI camera / RTSP IP camera
- Python 3.6+

## Installation

### Using Docker (Recommended)

1. Install Docker on your Jetson Nano:
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   ```

2. Build the Docker image:
   ```bash
   docker build -t smart-surveillance .
   ```

3. Run the container:
   ```bash
   docker run --runtime nvidia --network host -e DISPLAY=$DISPLAY --privileged -v /tmp/.X11-unix/:/tmp/.X11-unix/ smart-surveillance
   ```

### Manual Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/username/smart-surveillance-system.git
   cd smart-surveillance-system
   ```

2. Install dependencies:
   ```bash
   sudo apt-get update && sudo apt-get install -y \
       libgl1 \
       libglib2.0-0 \
       python3-pip \
       python3-dev \
       git \
       wget
   ```

3. Install Python packages:
   ```bash
   pip3 install -r requirements.txt
   ```

4. Download YOLOv8 model:
   ```bash
   wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
   ```

5. Run the setup script:
   ```bash
   bash scripts/setup.sh
   ```

## Configuration

The system is configured via a JSON file located at `config/config.json`. The main configuration options include:

### Model Configuration
```json
"model": {
    "path": "yolov8n.pt",
    "confidence_threshold": 0.45,
    "use_tensorrt": true,
    "target_classes": [0]
}
```

### Camera Configuration
```json
"camera": {
    "source": "0",  // Use "rtsp://..." for IP cameras
    "width": 640,
    "height": 480
}
```

### Zone Configuration
```json
"zones": {
    "zone1": {
        "name": "Main Entrance",
        "points": [[100, 400], [300, 400], [300, 300], [100, 300]],
        "color": [0, 0, 255],
        "alert_enabled": true
    }
}
```

### Alert Configuration
```json
"alerts": {
    "enabled": true,
    "cooldown_seconds": 60,
    "history_dir": "logs/alerts",
    "email": {
        "enabled": false,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "username": "your-email@gmail.com",
        "password": "your-app-password",
        "from_email": "your-email@gmail.com",
        "to_email": "recipient@example.com",
        "subject": "Intruder Alert!"
    },
    "telegram": {
        "enabled": false,
        "bot_token": "your-bot-token",
        "chat_id": "your-chat-id"
    }
}
```

## Usage

### Basic Run
```bash
python3 src/intruder_detection.py
```

### Run with Custom Configuration
```bash
python3 src/intruder_detection.py --config custom_config.json
```

### Low-power Mode
```bash
python3 src/intruder_detection.py --low-power
```

### Benchmark Mode
```bash
python3 src/intruder_detection.py --benchmark
```

### Configure Detection Zones
```bash
python3 scripts/configure_zones.py
```

## Optimizing Performance

To achieve the best performance on Jetson Nano:

1. **Use TensorRT Optimization**
   - Ensure `use_tensorrt` is set to `true` in the configuration

2. **Use Smaller Models**
   - YOLOv8n is a good balance of speed and accuracy
   - For higher FPS, consider using a smaller model like YOLOv8n-tiny

3. **Optimize Resolution**
   - Lower input resolution (e.g., 416x416) increases FPS
   - Balance between detection accuracy and performance

4. **Enable Low-power Mode**
   - Use the `--low-power` flag for battery-powered deployments
   - This uses the 5W power mode on Jetson Nano

## Setting Up Alerts

### Email Alerts
1. For Gmail, enable 2-factor authentication
2. Generate an App Password
3. Use the app password in the configuration

### Telegram Alerts
1. Create a Telegram bot using BotFather
2. Get the bot token
3. Find your chat ID using the IDBot
4. Configure both in the settings

## Logs and Output

- Detection logs: `logs/detection.log`
- Alert images: `logs/alerts/`
- Recorded videos: `data/recordings/`
- Detection frames: `data/detections/`
- Benchmark results: `logs/benchmarks/`

## Troubleshooting

- **Low FPS**
  - Try a smaller model or lower resolution
  - Ensure TensorRT optimization is enabled
  - Check CPU/GPU temperature using `tegrastats`

- **Camera Connection Issues**
  - For RTSP cameras, verify the URL is correct
  - For USB cameras, try different indices (0, 1, etc.)

- **Alert Failures**
  - Verify network connectivity
  - Check credentials in the configuration
  - For Gmail, ensure App Password is correctly set


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- YOLOv8 by Ultralytics
- NVIDIA for Jetson Nano and TensorRT 

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Continuous Integration

The CI badge shows the status of automated tests that run in GitHub Actions. Note that these tests are limited to non-hardware dependent functionality since GitHub Actions runners don't have access to Jetson Nano hardware. For full testing, please run the tests on actual Jetson hardware.

```bash
# Run full test suite on Jetson hardware
python3 scripts/test_system.py

# Run benchmarks to test performance
python3 src/intruder_detection.py --benchmark
``` 