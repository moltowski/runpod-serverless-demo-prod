#!/usr/bin/env python3
"""
RunPod Serverless ComfyUI-WAN Handler v3 - FIXED
- Support RTX 5090 avec detection CUDA automatique
- Outputs correctement retournés avec base64
- Timeouts optimisés pour shutdown automatique
"""

import runpod
import json
import requests
import subprocess
import time
import os
import base64
from pathlib import Path
from threading import Thread
import logging
import glob

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state
comfy_process = None
comfy_ready = False
boot_start_time = time.time()

# Paths optimisés pour Network Volume avec symlinks
NETWORK_VOLUME = "/runpod-volume"
COMFY_DIR = "/ComfyUI"
COMFY_OUTPUT_DIR = f"{COMFY_DIR}/output"
NETWORK_OUTPUT_DIR = f"{NETWORK_VOLUME}/ComfyUI/output"

def setup_symlinks():
    """Create symlinks to network volume (run once at boot)"""
    symlinks = {
        f"{COMFY_DIR}/models": f"{NETWORK_VOLUME}/ComfyUI/models",
        f"{COMFY_DIR}/custom_nodes": f"{NETWORK_VOLUME}/ComfyUI/custom_nodes",
        f"{COMFY_DIR}/output": f"{NETWORK_VOLUME}/ComfyUI/output"
    }
    
    for link_path, target_path in symlinks.items():
        # Create target if doesn't exist
        Path(target_path).mkdir(parents=True, exist_ok=True)
        
        # Remove existing symlink/dir if exists
        if os.path.exists(link_path) or os.path.islink(link_path):
            if os.path.islink(link_path):
                os.unlink(link_path)
            elif os.path.isdir(link_path) and not os.listdir(link_path):
                os.rmdir(link_path)
        
        # Create symlink
        if not os.path.exists(link_path):
            os.symlink(target_path, link_path)
            logger.info(f"🔗 Symlink created: {link_path} -> {target_path}")

def detect_gpu():
    """Detect GPU type and configure CUDA accordingly"""
    try:
        # Get GPU info from nvidia-smi
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        gpu_name = result.stdout.strip()
        logger.info(f"🎮 GPU detected: {gpu_name}")
        
        # Configuration spécifique par GPU
        if "5090" in gpu_name:
            logger.info("🔧 Configuring for RTX 5090...")
            # Fix pour RTX 5090 : Force CUDA 12.4+ et disable certaines optimisations
            os.environ["CUDA_VISIBLE_DEVICES"] = "0"
            os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
            # Disable TF32 qui peut causer des problèmes sur 5090
            os.environ["TORCH_ALLOW_TF32_CUBLAS_OVERRIDE"] = "0"
            
        elif "4090" in gpu_name:
            logger.info("🔧 Configuring for RTX 4090...")
            os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:512"
            
        elif "A100" in gpu_name:
            logger.info("🔧 Configuring for A100...")
            # A100 a beaucoup de VRAM, pas besoin d'optimisations spéciales
            pass
        
        return gpu_name
        
    except Exception as e:
        logger.warning(f"⚠️ Could not detect GPU: {e}")
        return "Unknown GPU"

def start_comfyui():
    """Start ComfyUI server in background"""
    global comfy_process, comfy_ready
    
    if comfy_ready:
        return 0
    
    logger.info("🚀 Starting ComfyUI server...")
    start_time = time.time()
    
    try:
        # Launch ComfyUI
        logger.info(f"📂 ComfyUI directory: {COMFY_DIR}")
        comfy_process = subprocess.Popen([
            "python", f"{COMFY_DIR}/main.py",
            "--listen", "127.0.0.1",
            "--port", "8188",
            "--dont-print-server"
        ], cwd=COMFY_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        logger.info(f"🔄 ComfyUI process started (PID: {comfy_process.pid})")
        
        # Wait for server to be ready (timeout augmenté pour 5090)
        max_wait = 120  # 2 minutes max pour boot (5090 peut être lent)
        check_interval = 3
        last_log = 0
        
        while time.time() - start_time < max_wait:
            elapsed = time.time() - start_time
            
            # Log progress every 15s
            if int(elapsed) - last_log >= 15:
                logger.info(f"⏳ Still waiting for ComfyUI... {elapsed:.0f}s elapsed")
                last_log = int(elapsed)
                
                # Check if process is still running
                if comfy_process.poll() is not None:
                    logger.error(f"❌ ComfyUI process died (exit code: {comfy_process.returncode})")
                    # Try to get stderr
                    try:
                        stderr = comfy_process.stderr.read().decode('utf-8')
                        if stderr:
                            logger.error(f"ComfyUI stderr: {stderr[:500]}")
                    except:
                        pass
                    return None
            
            try:
                response = requests.get("http://127.0.0.1:8188", timeout=2)
                if response.status_code == 200:
                    comfy_ready = True
                    boot_time = time.time() - start_time
                    logger.info(f"✅ ComfyUI ready in {boot_time:.1f}s")
                    return boot_time
            except:
                pass
            
            time.sleep(check_interval)
        
        logger.error(f"❌ ComfyUI failed to start within {max_wait}s timeout")
        
        # Try to get process output for debugging
        if comfy_process.poll() is None:
            logger.error("⚠️ Process still running but not responding")
        else:
            logger.error(f"⚠️ Process exited with code: {comfy_process.returncode}")
        return None
        
    except Exception as e:
        logger.error(f"❌ Error starting ComfyUI: {e}")
        return None

def load_workflow(workflow_data=None):
    """Load workflow from input or file"""
    if workflow_data:
        logger.info("📄 Using provided workflow")
        return workflow_data
    
    # Fallback to default workflow
    logger.warning("⚠️ No workflow provided, cannot proceed")
    return None

def inject_workflow_params(workflow, prompt=None, seed=None, lora=None):
    """Inject parameters into workflow nodes"""
    
    # Inject prompt (cherche les nodes CLIPTextEncode ou TextInput)
    if prompt:
        for node_id, node in workflow.items():
            if isinstance(node, dict) and "inputs" in node:
                if "text" in node["inputs"]:
                    # C'est probablement un node de prompt
                    node["inputs"]["text"] = prompt
                    logger.info(f"💬 Prompt injected in node {node_id}")
                    break
    
    # Inject seed (cherche les nodes avec seed)
    if seed is not None:
        for node_id, node in workflow.items():
            if isinstance(node, dict) and "inputs" in node:
                if "seed" in node["inputs"]:
                    node["inputs"]["seed"] = seed
                    logger.info(f"🎲 Seed {seed} injected in node {node_id}")
                    break
    
    # Inject LoRA (cherche les nodes LoraLoader)
    if lora:
        for node_id, node in workflow.items():
            if isinstance(node, dict) and "class_type" in node:
                if "LoRA" in node["class_type"] or "Lora" in node["class_type"]:
                    if "lora_name" in node["inputs"]:
                        node["inputs"]["lora_name"] = lora
                        logger.info(f"🎨 LoRA {lora} injected in node {node_id}")
                        break
    
    return workflow

def submit_workflow(workflow):
    """Submit workflow to ComfyUI and wait for completion"""
    
    try:
        # Submit to ComfyUI
        response = requests.post(
            "http://127.0.0.1:8188/prompt",
            json={"prompt": workflow},
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"❌ Failed to submit workflow: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None
            
        result = response.json()
        prompt_id = result.get("prompt_id")
        
        if not prompt_id:
            logger.error(f"❌ No prompt_id in response: {result}")
            return None
        
        logger.info(f"📤 Workflow submitted: {prompt_id}")
        
        return wait_for_completion(prompt_id)
        
    except Exception as e:
        logger.error(f"❌ Error submitting workflow: {e}")
        return None

def wait_for_completion(prompt_id):
    """Wait for workflow completion and return outputs"""
    
    start_time = time.time()
    max_wait = 600  # 10 minutes max (ajusté pour vidéos longues)
    check_interval = 5  # Check toutes les 5s
    
    logger.info(f"⏳ Waiting for completion (max {max_wait}s)...")
    
    while time.time() - start_time < max_wait:
        try:
            # Check history
            response = requests.get("http://127.0.0.1:8188/history", timeout=10)
            
            if response.status_code == 200:
                history = response.json()
                
                if prompt_id in history:
                    result = history[prompt_id]
                    
                    # Check for errors
                    if "status" in result:
                        status_info = result["status"]
                        if status_info.get("completed", False):
                            # Success!
                            execution_time = time.time() - start_time
                            logger.info(f"✅ Workflow completed in {execution_time:.1f}s")
                            
                            return {
                                "success": True,
                                "execution_time": execution_time,
                                "outputs": result.get("outputs", {})
                            }
                        elif "messages" in status_info:
                            # Check for errors in messages
                            messages = status_info.get("messages", [])
                            for msg in messages:
                                if msg[0] == "execution_error":
                                    error_detail = msg[1]
                                    logger.error(f"❌ Execution error: {error_detail}")
                                    return {
                                        "success": False,
                                        "error": "Execution error",
                                        "details": error_detail,
                                        "execution_time": time.time() - start_time
                                    }
            
            # Log progress every 30s
            elapsed = time.time() - start_time
            if int(elapsed) % 30 == 0:
                logger.info(f"⏳ Still processing... {elapsed:.0f}s elapsed")
            
            time.sleep(check_interval)
            
        except Exception as e:
            logger.error(f"❌ Error checking completion: {e}")
            time.sleep(check_interval)
    
    logger.error(f"⏰ Workflow timeout after {max_wait}s")
    return {
        "success": False,
        "error": "Workflow execution timeout",
        "execution_time": max_wait
    }

def extract_output_files(outputs):
    """
    Extract output files from ComfyUI outputs and encode to base64
    FIXED: Now actually reads files and returns them
    """
    
    output_list = []
    
    for node_id, node_outputs in outputs.items():
        logger.info(f"📦 Processing outputs from node {node_id}")
        
        # Check for videos
        if "videos" in node_outputs:
            for video_info in node_outputs["videos"]:
                filename = video_info.get("filename")
                if filename:
                    # Chercher le fichier dans le dossier output
                    file_path = os.path.join(COMFY_OUTPUT_DIR, filename)
                    
                    if os.path.exists(file_path):
                        try:
                            # Read file and encode to base64
                            with open(file_path, "rb") as f:
                                file_data = f.read()
                            
                            file_size = len(file_data)
                            
                            # Only encode to base64 if file is not too large (< 100MB)
                            if file_size < 100 * 1024 * 1024:
                                base64_data = base64.b64encode(file_data).decode('utf-8')
                                
                                output_list.append({
                                    "type": "video",
                                    "filename": filename,
                                    "size_bytes": file_size,
                                    "path": file_path,
                                    "base64": base64_data
                                })
                                
                                logger.info(f"✅ Video encoded: {filename} ({file_size / 1024 / 1024:.1f} MB)")
                            else:
                                # File too large, just return metadata
                                output_list.append({
                                    "type": "video",
                                    "filename": filename,
                                    "size_bytes": file_size,
                                    "path": file_path,
                                    "note": "File too large for base64 encoding, stored on network volume"
                                })
                                
                                logger.warning(f"⚠️ Video too large for base64: {filename} ({file_size / 1024 / 1024:.1f} MB)")
                        
                        except Exception as e:
                            logger.error(f"❌ Error reading video {filename}: {e}")
                    else:
                        logger.warning(f"⚠️ Video file not found: {file_path}")
        
        # Check for images
        if "images" in node_outputs:
            for image_info in node_outputs["images"]:
                filename = image_info.get("filename")
                if filename:
                    file_path = os.path.join(COMFY_OUTPUT_DIR, filename)
                    
                    if os.path.exists(file_path):
                        try:
                            with open(file_path, "rb") as f:
                                file_data = f.read()
                            
                            file_size = len(file_data)
                            base64_data = base64.b64encode(file_data).decode('utf-8')
                            
                            output_list.append({
                                "type": "image",
                                "filename": filename,
                                "size_bytes": file_size,
                                "path": file_path,
                                "base64": base64_data
                            })
                            
                            logger.info(f"✅ Image encoded: {filename} ({file_size / 1024:.1f} KB)")
                        
                        except Exception as e:
                            logger.error(f"❌ Error reading image {filename}: {e}")
                    else:
                        logger.warning(f"⚠️ Image file not found: {file_path}")
    
    return output_list

def calculate_cost(execution_seconds, gpu_type):
    """Calculate estimated cost based on GPU type and execution time"""
    # RunPod pricing per second (approximatif, vérifier les tarifs actuels)
    gpu_costs = {
        "RTX 5090": 0.00044,  # ~$1.59/hr
        "RTX 4090": 0.00031,  # ~$1.11/hr
        "A100 80GB": 0.00076, # ~$2.74/hr
        "A100 40GB": 0.00067, # ~$2.41/hr
        "L40": 0.00053,       # ~$1.91/hr
    }
    
    # Trouver le tarif correspondant (match partiel)
    rate = 0.00031  # default (4090)
    for gpu_name, cost in gpu_costs.items():
        if gpu_name in gpu_type:
            rate = cost
            break
    
    return execution_seconds * rate

def handler(event):
    """
    Main handler function
    OPTIMIZED: Returns quickly after completion so worker can shutdown
    """
    global boot_start_time
    
    handler_start = time.time()
    job_input = event.get("input", {})
    
    # Extract parameters
    workflow_data = job_input.get("workflow")
    prompt = job_input.get("prompt")
    seed = job_input.get("seed")
    lora = job_input.get("lora")
    
    logger.info(f"🎬 Processing job...")
    if prompt:
        logger.info(f"💬 Prompt: {prompt[:80]}...")
    
    try:
        # Setup symlinks (first run only)
        setup_symlinks()
        
        # Detect GPU and configure
        gpu_type = detect_gpu()
        
        # Start ComfyUI if not ready
        comfy_boot_time = 0
        if not comfy_ready:
            comfy_boot_time = start_comfyui()
            if comfy_boot_time is None:
                return {
                    "status": "error",
                    "error": "Failed to start ComfyUI",
                    "help": "Check ComfyUI logs for details"
                }
        
        # Load workflow
        workflow = load_workflow(workflow_data)
        if not workflow:
            return {
                "status": "error",
                "error": "No workflow provided",
                "help": "Include 'workflow' in your input JSON"
            }
        
        # Inject parameters
        workflow = inject_workflow_params(workflow, prompt, seed, lora)
        
        # Submit and execute
        processing_start = time.time()
        result = submit_workflow(workflow)
        
        if not result or not result.get("success"):
            return {
                "status": "error",
                "error": "Workflow execution failed",
                "details": result.get("error") if result else "Unknown error",
                "metrics": {
                    "cold_start_time": round(handler_start - boot_start_time, 2),
                    "comfy_boot_time": round(comfy_boot_time, 2)
                }
            }
        
        # Extract outputs (NOW WITH BASE64!)
        logger.info("📦 Extracting output files...")
        output_files = extract_output_files(result["outputs"])
        
        # Calculate metrics
        total_time = time.time() - handler_start
        cold_start_time = handler_start - boot_start_time
        processing_time = result["execution_time"]
        cost_estimate = calculate_cost(total_time, gpu_type)
        
        logger.info(f"✅ Job completed in {total_time:.1f}s")
        logger.info(f"💰 Estimated cost: ${cost_estimate:.4f}")
        
        # Return result (worker will shutdown after this based on idle timeout)
        return {
            "status": "completed",
            "prompt": prompt,
            "seed": seed,
            "outputs": output_files,  # NOW CONTAINS BASE64 DATA!
            "metrics": {
                "cold_start_time": round(cold_start_time, 2),
                "comfy_boot_time": round(comfy_boot_time, 2),
                "processing_time": round(processing_time, 2),
                "total_time": round(total_time, 2),
                "cost": round(cost_estimate, 4)
            },
            "infrastructure": {
                "gpu_type": gpu_type,
                "worker_id": os.environ.get("RUNPOD_POD_ID", "local")
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Handler error: {e}")
        import traceback
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }

if __name__ == "__main__":
    logger.info("🚀 Starting RunPod Serverless Handler v3...")
    
    # Pre-warm: setup symlinks and start ComfyUI in background
    setup_symlinks()
    detect_gpu()
    Thread(target=start_comfyui, daemon=True).start()
    
    # Start RunPod serverless with optimal config
    runpod.serverless.start({
        "handler": handler,
        "return_aggregate_stream": False,
        # Config pour shutdown rapide après job
        "refresh_worker": True  # Force refresh after each job
    })
