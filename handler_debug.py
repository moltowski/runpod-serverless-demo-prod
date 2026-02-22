#!/usr/bin/env python3
"""
Handler de debug ultra-minimal
Just pour tester si le container reste up
"""

import time
import sys
import os

print("=" * 70, flush=True)
print("DEBUG HANDLER - STARTING", flush=True)
print("=" * 70, flush=True)

print(f"Python version: {sys.version}", flush=True)
print(f"Current dir: {os.getcwd()}", flush=True)
print(f"Files in /: {os.listdir('/')}", flush=True)

print("\n[1/5] Testing imports...", flush=True)

try:
    import torch
    print(f"  ✅ torch: {torch.__version__}", flush=True)
    print(f"  CUDA available: {torch.cuda.is_available()}", flush=True)
except Exception as e:
    print(f"  ❌ torch error: {e}", flush=True)

try:
    import runpod
    print(f"  ✅ runpod imported", flush=True)
except Exception as e:
    print(f"  ❌ runpod error: {e}", flush=True)
    sys.exit(1)

print("\n[2/5] Checking directories...", flush=True)

dirs_to_check = [
    "/ComfyUI",
    "/runpod-volume",
    "/ComfyUI/models",
    "/ComfyUI/custom_nodes",
]

for d in dirs_to_check:
    exists = os.path.exists(d)
    is_link = os.path.islink(d)
    print(f"  {d}: {'✅' if exists else '❌'} exists, {'🔗' if is_link else '📁'} {'link' if is_link else 'dir'}", flush=True)

print("\n[3/5] Defining minimal handler...", flush=True)

def handler(event):
    """Minimal handler that just returns OK"""
    print(f"[HANDLER] Job received: {event.get('input', {})}", flush=True)
    return {
        "status": "ok",
        "message": "Debug handler working!",
        "gpu": os.environ.get("RUNPOD_GPU_TYPE", "unknown")
    }

print("  ✅ Handler defined", flush=True)

print("\n[4/5] Starting RunPod serverless...", flush=True)

# CRITICAL: Add a small delay to ensure all stdout is flushed
import time
time.sleep(2)
sys.stdout.flush()
sys.stderr.flush()

try:
    print("  Calling runpod.serverless.start()...", flush=True)
    print(f"  Handler function: {handler}", flush=True)
    print(f"  Handler callable: {callable(handler)}", flush=True)
    
    # Test calling handler directly first
    try:
        test_result = handler({"input": {"test": "direct call"}})
        print(f"  ✅ Direct handler call works: {test_result}", flush=True)
    except Exception as e:
        print(f"  ❌ Direct handler call failed: {e}", flush=True)
    
    print("  Now starting serverless (this should block)...", flush=True)
    sys.stdout.flush()
    
    runpod.serverless.start({
        "handler": handler,
        "return_aggregate_stream": False
    })
    
    print("  ⚠️ runpod.serverless.start() returned (should block forever!)", flush=True)
except Exception as e:
    print(f"  ❌ Error starting serverless: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n[5/5] If you see this, runpod.serverless.start() didn't block!", flush=True)
print("Entering infinite loop to keep container alive...", flush=True)

# Safety: keep alive even if runpod.serverless.start() returns
while True:
    print(".", end="", flush=True)
    time.sleep(10)
