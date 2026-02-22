#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RunPod Serverless ComfyUI Handler - PRODUCTION READY
=====================================================
Combines diagnostic logging + full workflow processing
"""
import sys
import os
import time

# CRITICAL: Non-buffered output
os.environ['PYTHONUNBUFFERED'] = '1'

print("=" * 70, flush=True)
print("🚀 HANDLER PRODUCTION - STARTING", flush=True)
print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
print("=" * 70, flush=True)

try:
    # Core imports
    print("[1/10] Importing standard libs...", flush=True)
    import json
    import base64
    import traceback
    from pathlib import Path
    import subprocess
    from threading import Thread
    print("  ✅ Standard libs OK", flush=True)
    
    print("[2/10] Importing runpod...", flush=True)
    import runpod
    print("  ✅ runpod OK", flush=True)
    
    print("[3/10] Importing torch...", flush=True)
    import torch
    print(f"  ✅ torch {torch.__version__}, CUDA: {torch.cuda.is_available()}", flush=True)
    
    print("[4/10] Importing requests...", flush=True)
    import requests
    import logging
    print("  ✅ All imports OK", flush=True)
    
    # Setup logging
    print("[5/10] Setting up logging...", flush=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('/runpod-volume/handler_production.log')
        ]
    )
    logger = logging.getLogger(__name__)
    print("  ✅ Logging OK", flush=True)
    
    # Paths
    NETWORK_VOLUME = "/runpod-volume"
    COMFY_DIR = "/ComfyUI"
    COMFY_OUTPUT = f"{COMFY_DIR}/output"
    WORKFLOWS_BASE = f"{NETWORK_VOLUME}/workflow"
    
    # Fallback: Check if workflow exists in root (bundled in Docker)
    WORKFLOWS_FALLBACK = "/"
    
    # Global state
    comfy_process = None
    comfy_ready = False
    
    print("[6/10] Setting up directories...", flush=True)
    
    def ensure_symlinks():
        """Create symlinks to network volume"""
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
        """Ensure temp is a real dir (not symlink)"""
        temp_dir = f"{COMFY_DIR}/temp"
        if os.path.islink(temp_dir):
            os.unlink(temp_dir)
        os.makedirs(temp_dir, exist_ok=True)
        logger.info(f"✅ Temp dir: {temp_dir}")
    
    ensure_symlinks()
    ensure_temp_directory()
    print("  ✅ Directories OK", flush=True)
    
    print("[7/10] Checking system...", flush=True)
    
    # CUDA diagnostics
    if torch.cuda.is_available():
        logger.info(f"🎮 GPU: {torch.cuda.get_device_name(0)}")
        logger.info(f"💾 VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        
        # Test CUDA
        try:
            test = torch.zeros(1, device='cuda')
            del test
            logger.info("✅ CUDA test passed")
        except Exception as e:
            logger.error(f"❌ CUDA test failed: {e}")
    else:
        logger.warning("⚠️ CUDA not available - will use CPU")
    
    print("  ✅ System check OK", flush=True)
    
    print("[8/10] Starting ComfyUI...", flush=True)
    
    def start_comfyui():
        """Start ComfyUI server in background"""
        global comfy_process, comfy_ready
        
        logger.info("🚀 Starting ComfyUI server...")
        main_py = f"{COMFY_DIR}/main.py"
        
        if not os.path.exists(main_py):
            logger.error(f"❌ ComfyUI not found at {main_py}")
            return
        
        try:
            comfy_process = subprocess.Popen(
                ["python", main_py, "--listen", "127.0.0.1", "--port", "8188"],
                cwd=COMFY_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True
            )
            logger.info(f"✅ ComfyUI started (PID: {comfy_process.pid})")
            
            # Monitor output
            for line in comfy_process.stdout:
                line = line.strip()
                if line:
                    logger.info(f"[ComfyUI] {line}")
                    if "To see the GUI go to" in line or "Starting server" in line:
                        comfy_ready = True
                        logger.info("✅ ComfyUI is READY!")
                        
        except Exception as e:
            logger.error(f"❌ Failed to start ComfyUI: {e}")
            traceback.print_exc()
    
    def wait_for_comfyui(timeout=300):
        """Wait for ComfyUI to be ready"""
        logger.info(f"⏳ Waiting for ComfyUI (timeout: {timeout}s)...")
        deadline = time.time() + timeout
        start = time.time()
        
        while time.time() < deadline:
            try:
                resp = requests.get("http://127.0.0.1:8188", timeout=2)
                if resp.status_code == 200:
                    elapsed = int(time.time() - start)
                    logger.info(f"✅ ComfyUI ready! (took {elapsed}s)")
                    return True
            except:
                pass
            
            time.sleep(2)
        
        raise RuntimeError(f"❌ ComfyUI failed to start within {timeout}s")
    
    # Start ComfyUI in background thread
    Thread(target=start_comfyui, daemon=True).start()
    
    # Wait for ComfyUI to be ready
    wait_for_comfyui()
    
    print("  ✅ ComfyUI ready!", flush=True)
    
    print("[9/10] Defining handler...", flush=True)
    
    def load_workflow(workflow_name):
        """Load workflow JSON from network volume or fallback to bundled"""
        # Try network volume first
        workflow_path = f"{WORKFLOWS_BASE}/{workflow_name}.json"
        
        if not os.path.exists(workflow_path):
            # Fallback to bundled workflow in Docker image
            workflow_path = f"{WORKFLOWS_FALLBACK}{workflow_name}.json"
            logger.info(f"Using bundled workflow: {workflow_path}")
        
        if not os.path.exists(workflow_path):
            raise FileNotFoundError(f"Workflow not found: {workflow_name}.json (tried {WORKFLOWS_BASE} and {WORKFLOWS_FALLBACK})")
        
        with open(workflow_path, 'r') as f:
            return json.load(f)
    
    def inject_prompt(workflow, prompt_text, seed=None):
        """Inject prompt and seed into workflow"""
        for node_id, node in workflow.items():
            if node.get("class_type") == "CLIPTextEncode":
                if "inputs" in node and "text" in node["inputs"]:
                    node["inputs"]["text"] = prompt_text
                    logger.info(f"✅ Injected prompt into node {node_id}")
            
            if seed is not None:
                if node.get("class_type") == "KSampler":
                    if "inputs" in node:
                        node["inputs"]["seed"] = seed
                        logger.info(f"✅ Injected seed {seed} into KSampler {node_id}")
        
        return workflow
    
    def queue_workflow(workflow):
        """Queue workflow to ComfyUI"""
        url = "http://127.0.0.1:8188/prompt"
        payload = {"prompt": workflow}
        
        logger.info("📤 Sending workflow to ComfyUI...")
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        
        data = resp.json()
        prompt_id = data.get("prompt_id")
        logger.info(f"✅ Workflow queued! Prompt ID: {prompt_id}")
        
        return prompt_id
    
    def wait_for_completion(prompt_id, timeout=600):
        """Poll ComfyUI until workflow completes"""
        logger.info(f"⏳ Waiting for completion (timeout: {timeout}s)...")
        deadline = time.time() + timeout
        start = time.time()
        last_log = 0
        
        while time.time() < deadline:
            try:
                # Check history
                resp = requests.get(f"http://127.0.0.1:8188/history/{prompt_id}", timeout=5)
                
                if resp.status_code == 200:
                    history = resp.json()
                    
                    if prompt_id in history:
                        elapsed = int(time.time() - start)
                        logger.info(f"✅ Workflow completed in {elapsed}s!")
                        return history[prompt_id]
                
                # Log progress every 10s
                elapsed = int(time.time() - start)
                if elapsed - last_log >= 10:
                    logger.info(f"⏳ Still processing... ({elapsed}s elapsed)")
                    last_log = elapsed
                
            except Exception as e:
                logger.warning(f"Poll error: {e}")
            
            time.sleep(2)
        
        raise TimeoutError(f"Workflow did not complete within {timeout}s")
    
    def get_output_files(history_entry):
        """Extract output files from history"""
        outputs = []
        
        if "outputs" not in history_entry:
            logger.warning("⚠️ No 'outputs' key in history entry")
            return outputs
        
        for node_id, node_output in history_entry["outputs"].items():
            logger.info(f"🔍 Checking node {node_id}: {list(node_output.keys())}")
            
            # Handle standard images output
            if "images" in node_output:
                for img in node_output["images"]:
                    filename = img["filename"]
                    subfolder = img.get("subfolder", "")
                    
                    if subfolder:
                        file_path = f"{COMFY_OUTPUT}/{subfolder}/{filename}"
                    else:
                        file_path = f"{COMFY_OUTPUT}/{filename}"
                    
                    if os.path.exists(file_path):
                        outputs.append({
                            "type": "image" if filename.lower().endswith(('.png', '.jpg', '.jpeg')) else "video",
                            "path": file_path,
                            "filename": filename
                        })
                        logger.info(f"✅ Found image/video: {filename}")
            
            # Handle VHS_VideoCombine gifs output
            if "gifs" in node_output:
                for gif in node_output["gifs"]:
                    filename = gif["filename"]
                    subfolder = gif.get("subfolder", "")
                    
                    if subfolder:
                        file_path = f"{COMFY_OUTPUT}/{subfolder}/{filename}"
                    else:
                        file_path = f"{COMFY_OUTPUT}/{filename}"
                    
                    if os.path.exists(file_path):
                        outputs.append({
                            "type": "video",
                            "path": file_path,
                            "filename": filename
                        })
                        logger.info(f"✅ Found gif: {filename}")
        
        if not outputs:
            logger.warning(f"⚠️ No output files found in history. Scanned {len(history_entry['outputs'])} nodes.")
        
        return outputs
    
    def encode_file(file_path):
        """Encode file to base64"""
        with open(file_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def handler(event):
        """Main RunPod handler"""
        job_input = event.get("input", {})
        logger.info(f"📥 Job received: {list(job_input.keys())}")
        
        try:
            # Extract parameters
            workflow_name = job_input.get("workflow_name", "wan-2.2")
            prompt = job_input.get("prompt", "A beautiful sunset over mountains")
            seed = job_input.get("seed")
            
            logger.info(f"📝 Workflow: {workflow_name}")
            logger.info(f"📝 Prompt: {prompt}")
            logger.info(f"📝 Seed: {seed}")
            
            # Load and inject
            workflow = load_workflow(workflow_name)
            workflow = inject_prompt(workflow, prompt, seed)
            
            # Queue and wait
            prompt_id = queue_workflow(workflow)
            history = wait_for_completion(prompt_id, timeout=600)
            
            # Get outputs
            outputs = get_output_files(history)
            logger.info(f"✅ Found {len(outputs)} output files")
            
            # Encode outputs
            results = []
            for output in outputs:
                logger.info(f"📦 Encoding {output['filename']}...")
                encoded = encode_file(output['path'])
                
                results.append({
                    "filename": output["filename"],
                    "type": output["type"],
                    "data": encoded
                })
            
            return {
                "status": "success",
                "prompt_id": prompt_id,
                "outputs": results,
                "workflow": workflow_name,
                "prompt": prompt,
                "seed": seed
            }
            
        except Exception as e:
            logger.error(f"❌ Handler error: {e}")
            traceback.print_exc()
            
            return {
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    print("  ✅ Handler defined", flush=True)
    
    print("[10/10] Starting RunPod serverless...", flush=True)
    logger.info("=" * 70)
    logger.info("🎯 HANDLER READY - Waiting for jobs...")
    logger.info("=" * 70)
    
    # Start serverless (blocks forever)
    runpod.serverless.start({
        "handler": handler,
        "return_aggregate_stream": False
    })
    
    # Should never reach here
    logger.error("⚠️ runpod.serverless.start() returned unexpectedly!")

except Exception as e:
    print(f"❌ FATAL BOOT ERROR: {e}", flush=True)
    traceback.print_exc()
    
    # Persist error
    try:
        with open('/runpod-volume/boot_crash.log', 'w') as f:
            f.write(f"Boot crash at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Error: {e}\n\n")
            traceback.print_exc(file=f)
    except:
        pass
    
    sys.exit(1)

# Safety loop (should never reach)
print("⚠️ Entering safety loop (runpod.serverless.start didn't block!)", flush=True)
while True:
    time.sleep(60)
