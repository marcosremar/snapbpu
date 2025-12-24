#!/usr/bin/env python3
"""
Simple test script for Dumont Cloud Jobs
Just verifies the job system works correctly.
"""

import os
import time
from datetime import datetime

MARKER_PATH = "/workspace/.job_complete"
FAILED_MARKER = "/workspace/.job_failed"
LOG_FILE = "/workspace/job.log"

def log(msg):
    """Print and write to log file"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def main():
    log("=" * 60)
    log("Dumont Cloud Job Test - Simple Validation")
    log("=" * 60)

    try:
        # Test 1: Environment info
        log(f"Python: {os.popen('python --version').read().strip()}")
        log(f"Working directory: {os.getcwd()}")
        log(f"Files: {os.listdir('.')}")

        # Test 2: Check GPU
        log("Checking GPU...")
        try:
            import torch
            log(f"PyTorch version: {torch.__version__}")
            log(f"CUDA available: {torch.cuda.is_available()}")
            if torch.cuda.is_available():
                log(f"GPU: {torch.cuda.get_device_name(0)}")
                mem = torch.cuda.get_device_properties(0).total_memory / 1e9
                log(f"GPU Memory: {mem:.1f} GB")
        except ImportError:
            log("PyTorch not installed - this is expected for simple test")

        # Test 3: Simulate some work
        log("Simulating work (30 seconds)...")
        for i in range(6):
            time.sleep(5)
            log(f"  Progress: {(i+1)*5}/30 seconds...")

        # Create completion marker
        log("Creating completion marker...")
        os.makedirs(os.path.dirname(MARKER_PATH), exist_ok=True)
        with open(MARKER_PATH, "w") as f:
            f.write(f"Job completed at {datetime.now().isoformat()}\n")
            f.write("Test: Simple validation passed\n")

        log("=" * 60)
        log("JOB COMPLETED SUCCESSFULLY!")
        log("=" * 60)
        return 0

    except Exception as e:
        log(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

        with open(FAILED_MARKER, "w") as f:
            f.write(f"Job failed at {datetime.now().isoformat()}\n")
            f.write(f"Error: {str(e)}\n")

        return 1

if __name__ == "__main__":
    exit(main())
