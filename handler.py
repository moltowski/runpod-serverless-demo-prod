#!/usr/bin/env python3
"""
RunPod Serverless ComfyUI Handler v2
- Accepts any workflow JSON directly or by name
- Executes workflow as-is without modifications
- Returns output files (videos, images)
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

logging.basicConfig(level=logging.INFO, format='%(filename)-20s:%(lineno)-4d %(asctime)s %(message)s')
logger = logging.getLogger(__name__)

# Global state
comfy_process = None
comfy_ready = False
boot_start_time = time.time()

# Paths
WORKFLOWS_BASE = "/runpod-volume/workflow"
COMFY_OUTPUT = "/ComfyUI/output"


def ensure_comfyui_models_linked():
    """Link ComfyUI models dir to network volume"""
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
    """Link ComfyUI custom_nodes dir to network volume"""
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
    """Ensure /ComfyUI/temp exists"""
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
        return 0

    logger.info("🚀 Starting ComfyUI server...")
    ensure_comfyui_models_linked()
    ensure_comfyui_custom_nodes_linked()
    ensure_comfyui_temp()
    start_time = time.time()

    try:
        comfy_process = subprocess.Popen(
            ["python", "/ComfyUI/main.py", "--listen", "127.0.0.1", "--port", "8188"],
            cwd="/ComfyUI"
        )

        max_wait = 600  # 10 minutes for heavy models
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


def get_workflow(job_input):
    """
    Get workflow from input. Supports:
    - workflow: dict - direct workflow JSON
    - workflow_name: str - name of workflow file on pod (without .json)
    - workflow_base64: str - base64 encoded workflow JSON
    """
    
    # Direct workflow JSON
    if "workflow" in job_input and isinstance(job_input["workflow"], dict):
        logger.info("📄 Using workflow from request (direct JSON)")
        return job_input["workflow"], None
    
    # Base64 encoded workflow
    if "workflow_base64" in job_input:
        try:
            decoded = base64.b64decode(job_input["workflow_base64"]).decode('utf-8')
            workflow = json.loads(decoded)
            logger.info("📄 Using workflow from request (base64)")
            return workflow, None
        except Exception as e:
            return None, f"Failed to decode base64 workflow: {e}"
    
    # Workflow by name (file on pod)
    workflow_name = job_input.get("workflow_name", "wan-t2v")
    workflow_path = f"{WORKFLOWS_BASE}/{workflow_name}.json"
    
    if not os.path.exists(workflow_path):
        # List available workflows
        available = []
        if os.path.exists(WORKFLOWS_BASE):
            available = [f.replace('.json', '') for f in os.listdir(WORKFLOWS_BASE) if f.endswith('.json')]
        return None, f"Workflow '{workflow_name}' not found. Available: {available}"
    
    try:
        with open(workflow_path, 'r') as f:
            workflow = json.load(f)
        logger.info(f"📄 Loaded workflow from pod: {workflow_path}")
        return workflow, None
    except Exception as e:
        return None, f"Failed to load workflow: {e}"


def submit_workflow(workflow):
    """Submit workflow to ComfyUI exactly as provided"""
    try:
        response = requests.post(
            "http://127.0.0.1:8188/prompt",
            json={"prompt": workflow},
            timeout=30
        )

        if response.status_code != 200:
            error_text = response.text
            logger.error(f"❌ ComfyUI rejected workflow: {response.status_code} - {error_text}")
            return None, f"ComfyUI error {response.status_code}: {error_text}"

        result = response.json()
        prompt_id = result.get("prompt_id")
        logger.info(f"📤 Workflow submitted: {prompt_id}")
        return prompt_id, None

    except Exception as e:
        logger.error(f"❌ Error submitting workflow: {e}")
        return None, str(e)


def wait_for_completion(prompt_id, timeout=600):
    """Wait for workflow completion"""
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = requests.get("http://127.0.0.1:8188/history", timeout=10)
            if response.status_code == 200:
                history = response.json()

                if prompt_id in history:
                    result = history[prompt_id]
                    
                    # Check for errors
                    if result.get("status", {}).get("status_str") == "error":
                        error_msg = result.get("status", {}).get("messages", [])
                        return {
                            "success": False,
                            "error": "Workflow execution error",
                            "details": error_msg,
                            "execution_time": time.time() - start_time
                        }
                    
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

    return {
        "success": False,
        "error": "Workflow execution timeout",
        "execution_time": timeout
    }


def extract_outputs(outputs):
    """Extract and optionally encode output files"""
    files = []

    for node_id, node_outputs in outputs.items():
        # Videos
        if "videos" in node_outputs:
            for video in node_outputs["videos"]:
                if "filename" in video:
                    filepath = f"{COMFY_OUTPUT}/{video['filename']}"
                    file_info = {
                        "type": "video",
                        "filename": video["filename"],
                        "node_id": node_id
                    }
                    # Check file size and include base64 if small enough
                    if os.path.exists(filepath):
                        size = os.path.getsize(filepath)
                        file_info["size_bytes"] = size
                        file_info["path"] = filepath
                        # Include base64 for files under 50MB
                        if size < 50 * 1024 * 1024:
                            try:
                                with open(filepath, 'rb') as f:
                                    file_info["base64"] = base64.b64encode(f.read()).decode('utf-8')
                            except:
                                pass
                    files.append(file_info)

        # Images
        if "images" in node_outputs:
            for image in node_outputs["images"]:
                if "filename" in image:
                    filepath = f"{COMFY_OUTPUT}/{image['filename']}"
                    file_info = {
                        "type": "image",
                        "filename": image["filename"],
                        "node_id": node_id
                    }
                    if os.path.exists(filepath):
                        size = os.path.getsize(filepath)
                        file_info["size_bytes"] = size
                        file_info["path"] = filepath
                        # Include base64 for images under 10MB
                        if size < 10 * 1024 * 1024:
                            try:
                                with open(filepath, 'rb') as f:
                                    file_info["base64"] = base64.b64encode(f.read()).decode('utf-8')
                            except:
                                pass
                    files.append(file_info)

    return files


def handler(event):
    """
    Main handler - accepts any ComfyUI workflow
    
    Input options:
      - workflow: dict - Complete workflow JSON
      - workflow_name: str - Name of workflow file on pod (default: "wan-t2v")
      - workflow_base64: str - Base64 encoded workflow JSON
      - timeout: int - Execution timeout in seconds (default: 600)
    """
    global boot_start_time

    handler_start = time.time()
    job_input = event.get("input", {})
    timeout = job_input.get("timeout", 600)

    logger.info(f"🎬 New job received")

    try:
        # Get workflow
        workflow, error = get_workflow(job_input)
        if error:
            return {"status": "error", "error": error}

        # Start ComfyUI if needed
        if not comfy_ready:
            boot_time = start_comfyui()
            if boot_time is None:
                return {"status": "error", "error": "Failed to start ComfyUI"}
        else:
            boot_time = 0

        # Submit workflow as-is
        prompt_id, error = submit_workflow(workflow)
        if error:
            return {"status": "error", "error": error}

        # Wait for completion
        result = wait_for_completion(prompt_id, timeout=timeout)

        if not result.get("success"):
            return {
                "status": "error",
                "error": result.get("error", "Unknown error"),
                "details": result.get("details"),
                "execution_time": result.get("execution_time")
            }

        # Extract outputs
        output_files = extract_outputs(result["outputs"])

        total_time = time.time() - handler_start

        return {
            "status": "completed",
            "outputs": output_files,
            "metrics": {
                "comfy_boot_seconds": round(boot_time, 2),
                "execution_seconds": round(result["execution_time"], 2),
                "total_seconds": round(total_time, 2)
            },
            "worker": {
                "gpu": os.environ.get("RUNPOD_GPU_TYPE", "unknown"),
                "pod_id": os.environ.get("RUNPOD_POD_ID", "local")
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
    logger.info("🚀 Starting RunPod Serverless Handler v2...")

    # Pre-warm ComfyUI
    Thread(target=start_comfyui, daemon=True).start()

    runpod.serverless.start({
        "handler": handler,
        "return_aggregate_stream": False
    })
