#!/usr/bin/env python3
"""
Benchmarking Utility for Intruder Detection System
Measures and reports system performance metrics
"""

import time
import json
import logging
import numpy as np
from pathlib import Path
from datetime import datetime

logger = logging.getLogger('Benchmarking')

def run_benchmark(detection_system, frames=300, warmup_frames=30):
    """Run a benchmark on the detection system
    
    Args:
        detection_system: IntruderDetectionSystem instance
        frames (int): Number of frames to process for the benchmark
        warmup_frames (int): Number of frames to process before starting measurements
        
    Returns:
        dict: Benchmark results
    """
    logger.info(f"Starting benchmark with {frames} frames (warmup: {warmup_frames})")
    
    # Store original config settings
    original_display = detection_system.config['output']['display_video']
    original_save_video = detection_system.config['output']['save_video']
    original_save_frames = detection_system.config['output']['save_detection_frames']
    
    # Modify config for benchmarking
    detection_system.config['output']['display_video'] = False
    detection_system.config['output']['save_video'] = False
    detection_system.config['output']['save_detection_frames'] = False
    detection_system.perf_monitor.reset()
    
    # Get current timestamp for the benchmark name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        # Initialize the system
        detection_system.setup_camera()
        detection_system.setup_model()
        
        logger.info("Warming up...")
        # Warmup
        for _ in range(warmup_frames):
            ret, frame = detection_system.cap.read()
            if not ret:
                logger.error("Failed to capture frame during warmup")
                return None
            
            # Process frame
            results = detection_system.model(
                frame, 
                conf=detection_system.conf_threshold, 
                classes=detection_system.target_classes,
                verbose=False
            )
            detection_system.process_results(frame, results[0])
        
        # Reset performance metrics after warmup
        detection_system.perf_monitor.reset()
        
        logger.info("Running benchmark...")
        # Benchmark
        for i in range(frames):
            ret, frame = detection_system.cap.read()
            if not ret:
                logger.error(f"Failed to capture frame during benchmark at frame {i}")
                break
            
            # Start timing
            detection_system.perf_monitor.start_process_timer()
            
            # Process frame
            results = detection_system.model(
                frame, 
                conf=detection_system.conf_threshold, 
                classes=detection_system.target_classes,
                verbose=False
            )
            processed_frame, detections = detection_system.process_results(frame, results[0])
            
            # Stop timing
            detection_system.perf_monitor.stop_process_timer()
            
            # Report progress
            if (i + 1) % 50 == 0:
                logger.info(f"Processed {i + 1}/{frames} frames")
        
        # Calculate statistics
        fps = detection_system.perf_monitor.get_fps()
        process_time = detection_system.perf_monitor.get_process_time()
        memory_usage = detection_system.perf_monitor.get_memory_usage()
        temperature = detection_system.perf_monitor.get_temperature()
        
        # Print summary
        logger.info("\nBenchmark Results:")
        logger.info(f"Average FPS: {fps:.2f}")
        logger.info(f"Average Processing Time: {process_time:.2f} ms")
        if memory_usage > 0:
            logger.info(f"Average Memory Usage: {memory_usage:.2f} MB")
        if temperature > 0:
            logger.info(f"Average CPU Temperature: {temperature:.2f}°C")
        
        # System info
        system_info = get_system_info()
        logger.info("\nSystem Information:")
        for key, value in system_info.items():
            logger.info(f"{key}: {value}")
        
        # Save benchmark results
        results = {
            'timestamp': timestamp,
            'config': {
                'model_path': detection_system.config['model']['path'],
                'use_tensorrt': detection_system.config['model']['use_tensorrt'],
                'confidence_threshold': detection_system.config['model']['confidence_threshold'],
                'target_classes': detection_system.config['model']['target_classes'],
                'frame_width': detection_system.frame_width,
                'frame_height': detection_system.frame_height
            },
            'performance': {
                'fps': float(f"{fps:.2f}"),
                'processing_time_ms': float(f"{process_time:.2f}"),
                'memory_usage_mb': float(f"{memory_usage:.2f}") if memory_usage > 0 else None,
                'temperature_c': float(f"{temperature:.2f}") if temperature > 0 else None
            },
            'system_info': system_info,
            'frames_processed': min(i + 1, frames)
        }
        
        save_benchmark_results(results)
        
        return results
        
    finally:
        # Restore original config
        detection_system.config['output']['display_video'] = original_display
        detection_system.config['output']['save_video'] = original_save_video
        detection_system.config['output']['save_detection_frames'] = original_save_frames
        
        # Cleanup resources
        detection_system.cleanup()

def get_system_info():
    """Get information about the system
    
    Returns:
        dict: System information
    """
    system_info = {
        'jetson_model': 'Unknown',
        'tensorrt_version': 'Unknown',
        'cuda_version': 'Unknown',
        'python_version': 'Unknown'
    }
    
    # Try to get Jetson model
    try:
        with open('/proc/device-tree/model', 'r') as f:
            system_info['jetson_model'] = f.read().strip()
    except:
        pass
    
    # Try to get CUDA version
    try:
        import torch
        system_info['cuda_version'] = torch.version.cuda
    except:
        pass
    
    # Try to get Python version
    try:
        import sys
        system_info['python_version'] = sys.version.split()[0]
    except:
        pass
    
    # Try to get TensorRT version
    try:
        import tensorrt
        system_info['tensorrt_version'] = tensorrt.__version__
    except:
        pass
    
    return system_info

def save_benchmark_results(results):
    """Save benchmark results to a file
    
    Args:
        results (dict): Benchmark results
    """
    output_dir = Path("logs/benchmarks")
    output_dir.mkdir(exist_ok=True, parents=True)
    
    output_file = output_dir / f"benchmark_{results['timestamp']}.json"
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=4)
    
    logger.info(f"Benchmark results saved to {output_file}")

def compare_benchmarks(benchmark_dir="logs/benchmarks"):
    """Compare all benchmarks in the benchmark directory
    
    Args:
        benchmark_dir (str): Directory containing benchmark JSON files
        
    Returns:
        list: Sorted list of benchmarks by FPS
    """
    benchmark_dir = Path(benchmark_dir)
    if not benchmark_dir.exists():
        logger.error(f"Benchmark directory {benchmark_dir} does not exist")
        return []
    
    benchmark_files = list(benchmark_dir.glob("benchmark_*.json"))
    if not benchmark_files:
        logger.error(f"No benchmark files found in {benchmark_dir}")
        return []
    
    benchmarks = []
    for file in benchmark_files:
        try:
            with open(file, 'r') as f:
                benchmark = json.load(f)
                benchmarks.append(benchmark)
        except:
            logger.error(f"Failed to load benchmark file {file}")
    
    # Sort by FPS
    benchmarks.sort(key=lambda x: x['performance']['fps'], reverse=True)
    
    logger.info("\nBenchmark Comparison (sorted by FPS):")
    logger.info("----------------------------------------")
    for i, benchmark in enumerate(benchmarks):
        logger.info(f"{i+1}. {benchmark['timestamp']} - FPS: {benchmark['performance']['fps']}")
        logger.info(f"   Model: {benchmark['config']['model_path']}")
        logger.info(f"   TensorRT: {benchmark['config']['use_tensorrt']}")
        logger.info(f"   Resolution: {benchmark['config']['frame_width']}x{benchmark['config']['frame_height']}")
        logger.info(f"   Processing Time: {benchmark['performance']['processing_time_ms']} ms")
        logger.info("----------------------------------------")
    
    return benchmarks 