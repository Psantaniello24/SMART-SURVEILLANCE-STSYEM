#!/bin/bash
# Setup script for Smart Surveillance System on Jetson Nano

# Text color variables
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Smart Surveillance System Setup ===${NC}"
echo -e "${BLUE}This script will help you set up the Smart Surveillance System on your Jetson Nano.${NC}"
echo

# Check if running on Jetson Nano
if [ -f /etc/nv_tegra_release ]; then
    echo -e "${GREEN}Detected Jetson device.${NC}"
else
    echo -e "${YELLOW}Warning: This doesn't appear to be a Jetson device.${NC}"
    echo -e "${YELLOW}The setup might not work correctly.${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Setup aborted.${NC}"
        exit 1
    fi
fi

# Create directories
echo -e "${BLUE}Creating directories...${NC}"
mkdir -p config logs/alerts data/recordings data/detections logs/benchmarks
echo -e "${GREEN}Created all necessary directories.${NC}"

# Install system dependencies
echo -e "${BLUE}Installing system dependencies...${NC}"
sudo apt-get update
sudo apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    python3-pip \
    python3-dev \
    git \
    wget

# Check for Python3
echo -e "${BLUE}Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1)
echo -e "${GREEN}Found $PYTHON_VERSION${NC}"

# Create virtual environment (optional)
echo -e "${BLUE}Do you want to create a Python virtual environment? (Recommended)${NC}"
read -p "Create virtual environment? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Installing virtualenv...${NC}"
    pip3 install virtualenv
    
    echo -e "${BLUE}Creating virtual environment...${NC}"
    python3 -m virtualenv venv
    
    echo -e "${BLUE}Activating virtual environment...${NC}"
    source venv/bin/activate
    
    echo -e "${GREEN}Virtual environment created and activated.${NC}"
    echo -e "${YELLOW}Note: You will need to activate the virtual environment each time with:${NC}"
    echo -e "${YELLOW}source venv/bin/activate${NC}"
fi

# Install Python dependencies
echo -e "${BLUE}Installing Python dependencies...${NC}"
pip3 install -r requirements.txt
echo -e "${GREEN}Python dependencies installed.${NC}"

# Download YOLOv8 model if it doesn't exist
if [ ! -f "yolov8n.pt" ]; then
    echo -e "${BLUE}Downloading YOLOv8n model...${NC}"
    wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
    echo -e "${GREEN}YOLOv8n model downloaded.${NC}"
else
    echo -e "${GREEN}YOLOv8n model already exists.${NC}"
fi

# Configure camera settings
echo -e "${BLUE}Do you want to configure camera settings now?${NC}"
read -p "Configure camera? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Select camera type:${NC}"
    echo "1) USB Camera"
    echo "2) RTSP Camera"
    read -p "Camera type (1/2): " camera_type
    
    if [ "$camera_type" == "1" ]; then
        read -p "Enter USB camera index (usually 0): " camera_index
        sed -i "s/\"source\": \".*\"/\"source\": \"$camera_index\"/" config/config.json
        echo -e "${GREEN}Camera configured to use USB index $camera_index.${NC}"
    elif [ "$camera_type" == "2" ]; then
        read -p "Enter RTSP URL: " rtsp_url
        sed -i "s|\"source\": \".*\"|\"source\": \"$rtsp_url\"|" config/config.json
        echo -e "${GREEN}Camera configured to use RTSP URL.${NC}"
    else
        echo -e "${RED}Invalid selection.${NC}"
    fi
fi

# Configure alert settings
echo -e "${BLUE}Do you want to configure alert settings now?${NC}"
read -p "Configure alerts? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Select alert method:${NC}"
    echo "1) Email"
    echo "2) Telegram"
    echo "3) Both"
    echo "4) Skip"
    read -p "Alert method (1/2/3/4): " alert_method
    
    if [[ "$alert_method" == "1" || "$alert_method" == "3" ]]; then
        echo -e "${BLUE}Configuring Email alerts:${NC}"
        read -p "SMTP Server: " smtp_server
        read -p "SMTP Port: " smtp_port
        read -p "Email Username: " email_username
        read -p "Email Password: " email_password
        read -p "From Email: " from_email
        read -p "To Email: " to_email
        
        # Update config.json
        sed -i "s/\"enabled\": false/\"enabled\": true/" config/config.json
        sed -i "s/\"smtp_server\": \".*\"/\"smtp_server\": \"$smtp_server\"/" config/config.json
        sed -i "s/\"smtp_port\": [0-9]*/\"smtp_port\": $smtp_port/" config/config.json
        sed -i "s/\"username\": \".*\"/\"username\": \"$email_username\"/" config/config.json
        sed -i "s/\"password\": \".*\"/\"password\": \"$email_password\"/" config/config.json
        sed -i "s/\"from_email\": \".*\"/\"from_email\": \"$from_email\"/" config/config.json
        sed -i "s/\"to_email\": \".*\"/\"to_email\": \"$to_email\"/" config/config.json
        
        echo -e "${GREEN}Email alerts configured.${NC}"
    fi
    
    if [[ "$alert_method" == "2" || "$alert_method" == "3" ]]; then
        echo -e "${BLUE}Configuring Telegram alerts:${NC}"
        read -p "Bot Token: " bot_token
        read -p "Chat ID: " chat_id
        
        # Update config.json
        sed -i "s/\"enabled\": false/\"enabled\": true/" config/config.json
        sed -i "s/\"bot_token\": \".*\"/\"bot_token\": \"$bot_token\"/" config/config.json
        sed -i "s/\"chat_id\": \".*\"/\"chat_id\": \"$chat_id\"/" config/config.json
        
        echo -e "${GREEN}Telegram alerts configured.${NC}"
    fi
fi

# Make the main script executable
chmod +x src/intruder_detection.py

echo
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo -e "${BLUE}You can now run the system with:${NC}"
echo -e "${YELLOW}python3 src/intruder_detection.py${NC}"
echo
echo -e "${BLUE}For low-power mode:${NC}"
echo -e "${YELLOW}python3 src/intruder_detection.py --low-power${NC}"
echo
echo -e "${BLUE}For benchmarking:${NC}"
echo -e "${YELLOW}python3 src/intruder_detection.py --benchmark${NC}"
echo
echo -e "${GREEN}Enjoy your Smart Surveillance System!${NC}" 