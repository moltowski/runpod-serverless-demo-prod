#!/usr/bin/env python3
"""
RunPod Serverless ComfyUI-WAN Handler (Network Storage Optimized)
Optimized for demo purposes with detailed metrics
"""

import runpod
import json
import requests
import subprocess
import time
import os
import uuid
from pathlib import Path
from threading import Thread
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state
comfy_process = None
comfy_ready = False
boot_start_time = time.time()

# Network storage paths (RunPod mounts network volume at /runpod-volume)
MODELS_BASE = "/runpod-volume/ComfyUI/models"
WORKFLOWS_BASE = "/runpod-volume/workflow"
OUTPUT_BASE = "/runpod-volume/temp"
COMFY_OUTPUT = "/ComfyUI/output"

def ensure_directories():
    """Ensure required directories exist"""
    dirs = [OUTPUT_BASE, COMFY_OUTPUT]
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)

def ensure_comfyui_models_linked():
    """Link ComfyUI models dir to network volume so ComfyUI finds models at /ComfyUI/models/"""
    import shutil
    comfy_models = "/ComfyUI/models"
    volume_models = "/runpod-volume/ComfyUI/models"
    if not os.path.exists(volume_models):
        return
    if os.path.islink(comfy_models):
        return
    if os.path.exists(comfy_models):
        try:
            shutil.rmtree(comfy_models)
        except Exception as e:
            logger.warning(f"Could not remove {comfy_models}: {e}")
            return
    try:
        os.symlink(volume_models, comfy_models)
        logger.info(f"✅ Linked {comfy_models} -> {volume_models}")
    except Exception as e:
        logger.warning(f"Could not symlink models: {e}")

def ensure_comfyui_custom_nodes_linked():
    """Link ComfyUI custom_nodes dir to network volume so ComfyUI finds custom nodes"""
    import shutil
    comfy_custom_nodes = "/ComfyUI/custom_nodes"
    volume_custom_nodes = "/runpod-volume/ComfyUI/custom_nodes"
    if not os.path.exists(volume_custom_nodes):
        return
    if os.path.islink(comfy_custom_nodes):
        return
    if os.path.exists(comfy_custom_nodes):
        try:
            shutil.rmtree(comfy_custom_nodes)
        except Exception as e:
            logger.warning(f"Could not remove {comfy_custom_nodes}: {e}")
            return
    try:
        os.symlink(volume_custom_nodes, comfy_custom_nodes)
        logger.info(f"✅ Linked {comfy_custom_nodes} -> {volume_custom_nodes}")
    except Exception as e:
        logger.warning(f"Could not symlink custom_nodes: {e}")

def ensure_comfyui_temp():
    """Ensure /ComfyUI/temp exists as a directory (ComfyUI needs it)"""
    import shutil
    temp_dir = "/ComfyUI/temp"
    if os.path.islink(temp_dir):
        try:
            os.unlink(temp_dir)
        except:
            pass
    if not os.path.isdir(temp_dir):
        try:
            if os.path.exists(temp_dir):
                os.remove(temp_dir)
            os.makedirs(temp_dir, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create {temp_dir}: {e}")

def start_comfyui():
    """Start ComfyUI server in background"""
    global comfy_process, comfy_ready
    
    if comfy_ready:
        return
    
    logger.info("🚀 Starting ComfyUI server...")
    ensure_comfyui_models_linked()
    ensure_comfyui_custom_nodes_linked()
    ensure_comfyui_temp()
    start_time = time.time()
    
    try:
        comfy_process = subprocess.Popen([
            "python", "/ComfyUI/main.py",
            "--listen", "127.0.0.1",
            "--port", "8188"
        ], cwd="/ComfyUI")
        
        # Wait for server to be ready (14B models can take 6-10 min to load)
        max_wait = 600  # 10 minutes
        while time.time() - start_time < max_wait:
            try:
                response = requests.get("http://127.0.0.1:8188", timeout=2)
                if response.status_code == 200:
                    comfy_ready = True
                    boot_time = time.time() - start_time
                    logger.info(f"✅ ComfyUI ready in {boot_time:.1f}s")
                    return boot_time
            except:
                time.sleep(2)
        
        logger.error("❌ ComfyUI failed to start within timeout")
        return None
        
    except Exception as e:
        logger.error(f"❌ Error starting ComfyUI: {e}")
        return None

def check_models():
    """Check if required models are available on network storage"""
    required_models = {
        "unet_high_noise": f"{MODELS_BASE}/diffusion_models/wan2.2_t2v_high_noise_14B_fp16.safetensors",
        "unet_low_noise": f"{MODELS_BASE}/diffusion_models/wan2.2_t2v_low_noise_14B_fp16.safetensors",
        "vae": f"{MODELS_BASE}/vae/wan_2.1_vae.safetensors",
        "clip": f"{MODELS_BASE}/clip/umt5_xxl_fp8_e4m3fn_scaled.safetensors"
    }
    
    available = {}
    for name, path in required_models.items():
        available[name] = os.path.exists(path)
        logger.info(f"🔍 Model {name}: {'✅ Found' if available[name] else '❌ Missing'} at {path}")
    
    return available

def load_workflow_template(workflow_type="test-workflow-api"):
    """Load workflow JSON from network storage"""
    workflow_path = f"{WORKFLOWS_BASE}/{workflow_type}.json"
    
    # Fallback to basic WAN workflow if file not found
    if not os.path.exists(workflow_path):
        logger.warning(f"⚠️ Workflow {workflow_path} not found, using basic template")
        return get_basic_wan_workflow()
    
    try:
        with open(workflow_path, 'r') as f:
            workflow = json.load(f)
        logger.info(f"📄 Loaded workflow: {workflow_path}")
        return workflow
    except Exception as e:
        logger.error(f"❌ Error loading workflow: {e}")
        return get_basic_wan_workflow()

def get_basic_wan_workflow():
    """Basic WAN T2V workflow template"""
    return {
        "1": {
            "inputs": {
                "prompt": "Beautiful woman dancing, high quality",
                "width": 512,
                "height": 512,
                "frames": 48,
                "fps": 8,
                "seed": 42
            },
            "class_type": "WanT2VNode"
        }
    }

def submit_workflow(workflow, prompt="", seed=None):
    """Submit workflow to ComfyUI and wait for completion"""
    
    # Update workflow with inputs
    if prompt:
        # Find text input node and update
        for node_id, node_data in workflow.items():
            if "prompt" in node_data.get("inputs", {}):
                node_data["inputs"]["prompt"] = prompt
                break
    
    if seed:
        # Find seed input and update
        for node_id, node_data in workflow.items():
            if "seed" in node_data.get("inputs", {}):
                node_data["inputs"]["seed"] = seed
                break
    
    # Submit to ComfyUI
    try:
        response = requests.post(
            "http://127.0.0.1:8188/prompt",
            json={"prompt": workflow},
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"❌ Failed to submit workflow: {response.status_code}")
            return None
        
        result = response.json()
        prompt_id = result["prompt_id"]
        logger.info(f"📤 Workflow submitted: {prompt_id}")
        
        return wait_for_completion(prompt_id)
        
    except Exception as e:
        logger.error(f"❌ Error submitting workflow: {e}")
        return None

def wait_for_completion(prompt_id):
    """Wait for workflow completion and return outputs"""
    
    start_time = time.time()
    max_wait = 300  # 5 minutes timeout
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get("http://127.0.0.1:8188/history", timeout=10)
            if response.status_code == 200:
                history = response.json()
                
                if prompt_id in history:
                    result = history[prompt_id]
                    if "outputs" in result:
                        execution_time = time.time() - start_time
                        logger.info(f"✅ Workflow completed in {execution_time:.1f}s")
                        return {
                            "success": True,
                            "execution_time": execution_time,
                            "outputs": result["outputs"]
                        }
            
            time.sleep(3)
            
        except Exception as e:
            logger.error(f"❌ Error checking completion: {e}")
            time.sleep(5)
    
    logger.error(f"❌ Workflow timeout after {max_wait}s")
    return {
        "success": False,
        "error": "Workflow execution timeout",
        "execution_time": max_wait
    }

def extract_output_files(outputs):
    """Extract file paths from ComfyUI outputs"""
    files = []
    
    for node_id, node_outputs in outputs.items():
        # Check for videos
        if "videos" in node_outputs:
            for video in node_outputs["videos"]:
                if "filename" in video:
                    files.append({
                        "type": "video",
                        "filename": video["filename"],
                        "path": f"/ComfyUI/output/{video['filename']}"
                    })
        
        # Check for images
        if "images" in node_outputs:
            for image in node_outputs["images"]:
                if "filename" in image:
                    files.append({
                        "type": "image", 
                        "filename": image["filename"],
                        "path": f"/ComfyUI/output/{image['filename']}"
                    })
    
    return files

def calculate_cost(execution_seconds, gpu_type="RTX 4090 PRO"):
    """Calculate estimated cost based on execution time"""
    # RunPod pricing (approximate)
    gpu_costs = {
        "RTX 4090 PRO": 0.00031,  # per second
        "L4": 0.00019,
        "L40": 0.00053,
        "A100": 0.00076
    }
    
    rate = gpu_costs.get(gpu_type, 0.00031)
    return execution_seconds * rate

def handler(event):
    """Main handler function"""
    global boot_start_time
    
    handler_start = time.time()
    job_input = event.get("input", {})
    
    # Extract parameters
    prompt = job_input.get("prompt", "Beautiful woman, NSFW, high quality")
    workflow_type = job_input.get("workflow_type", "test-workflow-api") 
    seed = job_input.get("seed", int(time.time()))
    
    logger.info(f"🎬 Processing job: {prompt[:50]}...")
    
    try:
        # Ensure directories
        ensure_directories()
        
        # Check models availability
        models_status = check_models()
        if not any(models_status.values()):
            return {
                "error": "No models found on network storage",
                "models_status": models_status,
                "help": "Make sure models are uploaded to /workspace/models/"
            }
        
        # Start ComfyUI if not ready
        comfy_boot_time = 0
        if not comfy_ready:
            comfy_boot_time = start_comfyui()
            if comfy_boot_time is None:
                return {"error": "Failed to start ComfyUI"}
        
        # Load workflow
        workflow = load_workflow_template(workflow_type)
        
        # Submit and execute
        processing_start = time.time()
        result = submit_workflow(workflow, prompt, seed)
        
        if not result or not result.get("success"):
            return {
                "error": "Workflow execution failed",
                "details": result
            }
        
        # Extract outputs
        output_files = extract_output_files(result["outputs"])
        
        # Calculate metrics
        total_time = time.time() - handler_start
        cold_start_time = handler_start - boot_start_time
        processing_time = result["execution_time"]
        
        gpu_type = os.environ.get("RUNPOD_GPU_TYPE", "RTX 4090 PRO")
        cost_estimate = calculate_cost(total_time, gpu_type)
        
        return {
            "status": "completed",
            "prompt": prompt,
            "seed": seed,
            "outputs": output_files,
            "metrics": {
                "cold_start_seconds": round(cold_start_time, 2),
                "comfy_boot_seconds": round(comfy_boot_time, 2),
                "processing_seconds": round(processing_time, 2),
                "total_seconds": round(total_time, 2),
                "cost_estimate_usd": round(cost_estimate, 4)
            },
            "infrastructure": {
                "gpu_type": gpu_type,
                "worker_id": os.environ.get("RUNPOD_POD_ID", "local"),
                "models_status": models_status
            },
            "demo_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC")
        }
        
    except Exception as e:
        logger.error(f"❌ Handler error: {e}")
        return {
            "error": str(e),
            "status": "failed"
        }

if __name__ == "__main__":
    logger.info("🚀 Starting RunPod Serverless Handler...")
    
    # Pre-warm ComfyUI
    Thread(target=start_comfyui, daemon=True).start()
    
    # Start RunPod serverless
    runpod.serverless.start({
        "handler": handler,
        "return_aggregate_stream": False
    })
