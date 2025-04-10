FROM nvcr.io/nvidia/l4t-pytorch:r35.2.1-pth2.0-py3

# TensorRT already included in the base image

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    python3-pip \
    python3-dev \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Install YOLOv8 explicitly
RUN pip3 install --no-cache-dir ultralytics

# Download YOLOv8n model
RUN wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt

# Download TensorRT conversion tools
RUN pip3 install --no-cache-dir onnx onnxruntime-gpu

# Copy application files
COPY . .

# Create necessary directories
RUN mkdir -p logs/alerts data/recordings data/detections logs/benchmarks

# Set environment variables
ENV PYTHONPATH="${PYTHONPATH}:/app"
ENV TZ=UTC

# Make script executable
RUN chmod +x src/intruder_detection.py

# Expose port if needed later for web interface
EXPOSE 8000

# Run in low-power mode by default
CMD ["python3", "src/intruder_detection.py", "--low-power"]

# Alternative run command with benchmarking
# CMD ["python3", "src/intruder_detection.py", "--benchmark", "--config", "config/config.json"] 