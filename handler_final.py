#!/usr/bin/env python3
"""
Handler FINAL avec toutes les fixes DeepSearch
"""
import sys
import os
import time

# CRITICAL: Non-buffered output + early logging
sys.stdout = sys.stderr = open('/tmp/handler_boot.log', 'w', buffering=1)
os.environ['PYTHONUNBUFFERED'] = '1'

print("=" * 70, flush=True)
print("HANDLER FINAL - STARTING", flush=True)
print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
print("=" * 70, flush=True)

try:
    print("[1/8] Importing critical modules...", flush=True)
    import json
    import base64
    import traceback
    from pathlib import Path
    print("  ✅ Standard libs OK", flush=True)
    
    print("[2/8] Importing runpod...", flush=True)
    import runpod
    print("  ✅ runpod OK", flush=True)
    
    print("[3/8] Importing torch...", flush=True)
    import torch
    print(f"  ✅ torch {torch.__version__}, CUDA: {torch.cuda.is_available()}", flush=True)
    
    print("[4/8] Importing other deps...", flush=True)
    import requests
    import subprocess
    import logging
    from threading import Thread
    print("  ✅ All imports OK", flush=True)
    
    print("[5/8] Setting up logging...", flush=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('/runpod-volume/handler.log')  # Persist on volume
        ]
    )
    logger = logging.getLogger(__name__)
    print("  ✅ Logging OK (stdout + /runpod-volume/handler.log)", flush=True)
    
    # Paths
    NETWORK_VOLUME = "/runpod-volume"
    COMFY_DIR = "/ComfyUI"
    COMFY_OUTPUT = f"{COMFY_DIR}/output"
    
    print("[6/8] Checking for test_input.json (can trigger local mode)...", flush=True)
    test_files = []
    for root, dirs, files in os.walk('.'):
        for f in files:
            if 'test' in f.lower() and f.endswith('.json'):
                test_files.append(os.path.join(root, f))
    if test_files:
        print(f"  ⚠️ Found test files: {test_files}", flush=True)
        print("  This may trigger local test mode!", flush=True)
    else:
        print("  ✅ No test files found", flush=True)
    
    print("[7/8] Setting up directories and symlinks...", flush=True)
    
    def ensure_symlinks():
        """Create symlinks safely"""
        symlinks = {
            f"{COMFY_DIR}/models": f"{NETWORK_VOLUME}/ComfyUI/models",
            f"{COMFY_DIR}/custom_nodes": f"{NETWORK_VOLUME}/ComfyUI/custom_nodes",
            f"{COMFY_DIR}/output": f"{NETWORK_VOLUME}/ComfyUI/output",
        }
        
        for link_path, target_path in symlinks.items():
            Path(target_path).mkdir(parents=True, exist_ok=True)
            
            if os.path.islink(link_path):
                current = os.readlink(link_path)
                if current == target_path:
                    logger.info(f"✅ Symlink OK: {link_path}")
                    continue
                os.unlink(link_path)
            elif os.path.exists(link_path):
                import shutil
                if os.path.isdir(link_path):
                    shutil.rmtree(link_path)
                else:
                    os.remove(link_path)
            
            os.symlink(target_path, link_path)
            logger.info(f"🔗 Created: {link_path} -> {target_path}")
    
    def ensure_temp_directory():
        """Ensure temp is a real dir"""
        temp_dir = f"{COMFY_DIR}/temp"
        if os.path.islink(temp_dir):
            os.unlink(temp_dir)
        os.makedirs(temp_dir, exist_ok=True)
        logger.info(f"✅ Temp dir: {temp_dir}")
    
    ensure_symlinks()
    ensure_temp_directory()
    print("  ✅ Directories OK", flush=True)
    
    # CRITICAL: Health check BEFORE starting serverless
    def wait_for_comfyui(timeout=300, port=8188):
        """Wait for ComfyUI to be ready before accepting jobs"""
        logger.info("Waiting for ComfyUI to be ready...")
        deadline = time.time() + timeout
        
        while time.time() < deadline:
            try:
                resp = requests.get(f"http://127.0.0.1:{port}", timeout=2)
                if resp.status_code == 200:
                    logger.info(f"✅ ComfyUI ready! (took {int(time.time() - (deadline - timeout))}s)")
                    return True
            except:
                pass
            time.sleep(2)
        
        raise RuntimeError(f"ComfyUI failed to start within {timeout}s")
    
    def start_comfyui():
        """Start ComfyUI server"""
        logger.info("🚀 Starting ComfyUI...")
        main_py = f"{COMFY_DIR}/main.py"
        
        if not os.path.exists(main_py):
            logger.error(f"❌ ComfyUI not found at {main_py}")
            return
        
        try:
            process = subprocess.Popen(
                ["python", main_py, "--listen", "127.0.0.1", "--port", "8188"],
                cwd=COMFY_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1
            )
            logger.info(f"ComfyUI process started (PID: {process.pid})")
        except Exception as e:
            logger.error(f"Failed to start ComfyUI: {e}")
            raise
    
    # Define handler
    def handler(event):
        """Main handler for RunPod jobs"""
        job_input = event.get("input", {})
        logger.info(f"📥 Job received: {list(job_input.keys())}")
        
        # For now, just return OK to test
        return {
            "status": "handler_ok",
            "message": "Handler reached successfully",
            "comfy_exists": os.path.exists(COMFY_DIR),
            "volume_exists": os.path.exists(NETWORK_VOLUME),
            "gpu": os.environ.get("RUNPOD_GPU_TYPE", "unknown")
        }
    
    print("[8/8] Starting ComfyUI then RunPod serverless...", flush=True)
    
    # Start ComfyUI in background
    Thread(target=start_comfyui, daemon=True).start()
    
    # CRITICAL: Wait for ComfyUI BEFORE starting serverless
    # Comment this out for initial test without ComfyUI
    # wait_for_comfyui()
    
    print("  ⏭️ Skipping ComfyUI wait for initial test", flush=True)
    print("  Now starting runpod.serverless.start()...", flush=True)
    sys.stdout.flush()
    
    # This MUST block forever
    runpod.serverless.start({
        "handler": handler,
        "return_aggregate_stream": False
    })
    
    # If we reach here, something is wrong
    print("⚠️ runpod.serverless.start() returned! This should never happen!", flush=True)
    logger.error("runpod.serverless.start() returned unexpectedly")

except Exception as e:
    print(f"❌ FATAL ERROR: {e}", flush=True)
    traceback.print_exc()
    
    # Write to volume for persistence
    try:
        with open('/runpod-volume/crash.log', 'w') as f:
            f.write(f"Crash at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Error: {e}\n\n")
            traceback.print_exc(file=f)
    except:
        pass
    
    sys.exit(1)

# Safety loop (should never reach if runpod.serverless.start() blocks)
print("Entering safety loop (this means runpod.serverless.start() didn't block!)", flush=True)
while True:
    print(".", end="", flush=True)
    time.sleep(10)
