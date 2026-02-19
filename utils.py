#!/usr/bin/env python3
"""
Utility functions for RunPod Serverless ComfyUI-WAN
"""

import os
import json
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def setup_network_storage_structure():
    """Create recommended directory structure on network storage"""
    
    base_dirs = [
        "/workspace/models/checkpoints",
        "/workspace/models/loras", 
        "/workspace/models/embeddings",
        "/workspace/models/upscale_models",
        "/workspace/workflows",
        "/workspace/temp",
        "/workspace/cache"
    ]
    
    created = []
    for dir_path in base_dirs:
        try:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            created.append(dir_path)
            logger.info(f"📁 Created directory: {dir_path}")
        except Exception as e:
            logger.error(f"❌ Failed to create {dir_path}: {e}")
    
    return created

def check_network_storage():
    """Check network storage availability and structure"""
    
    storage_info = {
        "mounted": os.path.ismount("/workspace"),
        "exists": os.path.exists("/workspace"),
        "writable": os.access("/workspace", os.W_OK) if os.path.exists("/workspace") else False,
        "structure": {}
    }
    
    if storage_info["exists"]:
        # Check expected directories
        expected_dirs = [
            "models/checkpoints",
            "models/loras", 
            "workflows",
            "temp"
        ]
        
        for rel_path in expected_dirs:
            full_path = f"/workspace/{rel_path}"
            storage_info["structure"][rel_path] = {
                "exists": os.path.exists(full_path),
                "files": []
            }
            
            # List files if directory exists
            if os.path.exists(full_path):
                try:
                    files = os.listdir(full_path)
                    storage_info["structure"][rel_path]["files"] = files[:10]  # Limit to first 10
                except Exception as e:
                    logger.error(f"❌ Error listing {full_path}: {e}")
    
    return storage_info

def get_model_info():
    """Get information about available models"""
    
    models_info = {
        "checkpoints": [],
        "loras": [],
        "total_size_gb": 0
    }
    
    # Check checkpoints
    checkpoints_dir = "/workspace/models/checkpoints"
    if os.path.exists(checkpoints_dir):
        for file in os.listdir(checkpoints_dir):
            if file.endswith(('.safetensors', '.ckpt', '.pt')):
                file_path = os.path.join(checkpoints_dir, file)
                try:
                    size_mb = os.path.getsize(file_path) / (1024*1024)
                    models_info["checkpoints"].append({
                        "name": file,
                        "size_mb": round(size_mb, 1)
                    })
                    models_info["total_size_gb"] += size_mb / 1024
                except Exception as e:
                    logger.error(f"❌ Error getting size for {file}: {e}")
    
    # Check LoRAs  
    loras_dir = "/workspace/models/loras"
    if os.path.exists(loras_dir):
        for root, dirs, files in os.walk(loras_dir):
            for file in files:
                if file.endswith(('.safetensors', '.ckpt', '.pt')):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, loras_dir)
                    try:
                        size_mb = os.path.getsize(file_path) / (1024*1024)
                        models_info["loras"].append({
                            "name": rel_path,
                            "size_mb": round(size_mb, 1)
                        })
                        models_info["total_size_gb"] += size_mb / 1024
                    except Exception as e:
                        logger.error(f"❌ Error getting size for {file}: {e}")
    
    models_info["total_size_gb"] = round(models_info["total_size_gb"], 2)
    return models_info

def create_demo_workflows():
    """Create basic workflow templates for demo"""
    
    workflows_dir = "/workspace/workflows"
    os.makedirs(workflows_dir, exist_ok=True)
    
    # Basic WAN T2V workflow
    wan_t2v = {
        "1": {
            "inputs": {
                "prompt": "Beautiful woman dancing, NSFW, high quality, 4K",
                "negative_prompt": "blurry, low quality, distorted",
                "width": 512,
                "height": 512, 
                "frames": 48,
                "fps": 8,
                "seed": 42,
                "steps": 20,
                "cfg": 7.5
            },
            "class_type": "WanT2VNode",
            "_meta": {
                "title": "WAN Text to Video"
            }
        }
    }
    
    # WAN I2V workflow
    wan_i2v = {
        "1": {
            "inputs": {
                "image": "",  # Will be provided
                "prompt": "Dynamic movement, NSFW, high quality",
                "frames": 48,
                "fps": 8,
                "seed": 42,
                "motion_strength": 1.0
            },
            "class_type": "WanI2VNode",
            "_meta": {
                "title": "WAN Image to Video"
            }
        }
    }
    
    workflows = {
        "wan-t2v.json": wan_t2v,
        "wan-i2v.json": wan_i2v
    }
    
    created = []
    for filename, workflow in workflows.items():
        try:
            file_path = os.path.join(workflows_dir, filename)
            with open(file_path, 'w') as f:
                json.dump(workflow, f, indent=2)
            created.append(filename)
            logger.info(f"📋 Created workflow: {filename}")
        except Exception as e:
            logger.error(f"❌ Error creating {filename}: {e}")
    
    return created

def benchmark_storage_speed():
    """Quick benchmark of network storage I/O speed"""
    
    if not os.path.exists("/workspace"):
        return {"error": "Network storage not mounted"}
    
    test_file = "/workspace/temp/storage_benchmark.tmp"
    test_size_mb = 10
    test_data = b'0' * (test_size_mb * 1024 * 1024)
    
    results = {}
    
    try:
        # Write speed
        start_time = time.time()
        with open(test_file, 'wb') as f:
            f.write(test_data)
        write_time = time.time() - start_time
        write_speed_mbps = test_size_mb / write_time
        
        results["write_mbps"] = round(write_speed_mbps, 1)
        
        # Read speed  
        start_time = time.time()
        with open(test_file, 'rb') as f:
            data = f.read()
        read_time = time.time() - start_time
        read_speed_mbps = test_size_mb / read_time
        
        results["read_mbps"] = round(read_speed_mbps, 1)
        
        # Cleanup
        os.remove(test_file)
        
        logger.info(f"💾 Storage benchmark - Write: {results['write_mbps']}MB/s, Read: {results['read_mbps']}MB/s")
        
    except Exception as e:
        results["error"] = str(e)
        logger.error(f"❌ Storage benchmark failed: {e}")
    
    return results

def log_system_info():
    """Log system information for debugging"""
    
    info = {
        "gpu": os.environ.get("RUNPOD_GPU_TYPE", "Unknown"),
        "worker_id": os.environ.get("RUNPOD_POD_ID", "local"),
        "cuda_visible": os.environ.get("CUDA_VISIBLE_DEVICES", "Unknown"),
        "storage_mounted": os.path.ismount("/workspace"),
        "comfyui_exists": os.path.exists("/ComfyUI"),
        "python_path": os.environ.get("PATH", ""),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC")
    }
    
    logger.info("🔍 System Info:")
    for key, value in info.items():
        logger.info(f"   {key}: {value}")
    
    return info