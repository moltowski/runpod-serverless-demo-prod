#!/usr/bin/env python3
"""
Handler ULTRA-SAFE avec catch dès le début
"""

# IMPORTS DE BASE SAFE
import sys
import os
import time

print("=" * 70, flush=True)
print("HANDLER STARTING - SAFE MODE", flush=True)
print("=" * 70, flush=True)

try:
    print("[1] Importing standard libs...", flush=True)
    import json
    import base64
    from pathlib import Path
    print("  ✅ Standard libs OK", flush=True)
    
    print("[2] Importing runpod...", flush=True)
    import runpod
    print("  ✅ runpod OK", flush=True)
    
    print("[3] Importing torch...", flush=True)
    import torch
    print(f"  ✅ torch {torch.__version__}, CUDA: {torch.cuda.is_available()}", flush=True)
    
    print("[4] Importing other dependencies...", flush=True)
    import requests
    import subprocess
    import logging
    from threading import Thread
    print("  ✅ All imports OK", flush=True)
    
    print("[5] Setting up logging...", flush=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s'
    )
    logger = logging.getLogger(__name__)
    print("  ✅ Logging OK", flush=True)
    
    # NOW import the real handler
    print("[6] Loading handler.py logic...", flush=True)
    
    # Paths
    NETWORK_VOLUME = "/runpod-volume"
    COMFY_DIR = "/ComfyUI"
    
    # Simple handler that returns info
    def handler(event):
        """Safe handler that just returns OK for now"""
        logger.info("Job received")
        job_input = event.get("input", {})
        
        return {
            "status": "handler_ok", 
            "message": "Handler reached successfully",
            "input_keys": list(job_input.keys()),
            "comfy_exists": os.path.exists(COMFY_DIR),
            "volume_exists": os.path.exists(NETWORK_VOLUME)
        }
    
    print("[7] Starting runpod serverless...", flush=True)
    sys.stdout.flush()
    
    runpod.serverless.start({
        "handler": handler,
        "return_aggregate_stream": False
    })
    
    print("[8] If you see this, runpod.serverless.start() returned!", flush=True)
    
except Exception as e:
    print(f"❌ FATAL ERROR: {e}", flush=True)
    import traceback
    print(traceback.format_exc(), flush=True)
    sys.exit(1)

# Safety loop
print("[9] Entering safety loop...", flush=True)
while True:
    print(".", end="", flush=True)
    time.sleep(10)
