#!/usr/bin/env python3
"""
Utils for RunPod Serverless ComfyUI Handler
"""

import os
import sys
import subprocess
import logging

logger = logging.getLogger(__name__)


def get_system_info():
    """Get system information for debugging"""
    info = {
        "python_version": sys.version,
        "cuda_home": os.environ.get("CUDA_HOME", "not set"),
        "ld_library_path": os.environ.get("LD_LIBRARY_PATH", "not set"),
    }
    
    # PyTorch info
    try:
        import torch
        info["torch_version"] = torch.__version__
        info["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            info["cuda_version"] = torch.version.cuda
            info["cudnn_version"] = str(torch.backends.cudnn.version())
            info["device_count"] = torch.cuda.device_count()
            if torch.cuda.device_count() > 0:
                info["device_name"] = torch.cuda.get_device_name(0)
                info["device_capability"] = torch.cuda.get_device_capability(0)
    except ImportError:
        info["torch_version"] = "not installed"
    except Exception as e:
        info["torch_error"] = str(e)
    
    # NVIDIA driver info
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=driver_version,name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(",")
            info["nvidia_driver"] = parts[0].strip() if len(parts) > 0 else "unknown"
            info["gpu_name"] = parts[1].strip() if len(parts) > 1 else "unknown"
            info["gpu_memory"] = parts[2].strip() if len(parts) > 2 else "unknown"
    except Exception as e:
        info["nvidia_error"] = str(e)
    
    return info


def log_system_info():
    """Log system info at startup"""
    info = get_system_info()
    
    logger.info("=" * 60)
    logger.info("SYSTEM DIAGNOSTICS")
    logger.info("=" * 60)
    logger.info(f"Python: {info.get('python_version', 'unknown')}")
    logger.info(f"PyTorch: {info.get('torch_version', 'unknown')}")
    logger.info(f"CUDA Available: {info.get('cuda_available', False)}")
    
    if info.get('cuda_available'):
        logger.info(f"CUDA Version: {info.get('cuda_version', 'unknown')}")
        logger.info(f"cuDNN Version: {info.get('cudnn_version', 'unknown')}")
        logger.info(f"Device: {info.get('device_name', 'unknown')}")
        logger.info(f"Compute Capability: {info.get('device_capability', 'unknown')}")
    
    logger.info(f"NVIDIA Driver: {info.get('nvidia_driver', 'unknown')}")
    logger.info(f"GPU: {info.get('gpu_name', 'unknown')}")
    logger.info(f"VRAM: {info.get('gpu_memory', 'unknown')}")
    logger.info("=" * 60)
    
    return info


def check_cuda_compatibility():
    """
    Check if PyTorch CUDA is compatible with the current GPU.
    Returns (compatible: bool, message: str)
    """
    try:
        import torch
        
        if not torch.cuda.is_available():
            return False, "CUDA not available in PyTorch"
        
        # Try to allocate a small tensor on GPU
        try:
            test_tensor = torch.zeros(1, device='cuda')
            del test_tensor
            return True, "CUDA working correctly"
        except RuntimeError as e:
            error_msg = str(e)
            if "sm_" in error_msg:
                return False, f"GPU architecture not supported: {error_msg}"
            elif "driver" in error_msg.lower():
                return False, f"Driver issue: {error_msg}"
            else:
                return False, f"CUDA error: {error_msg}"
                
    except ImportError:
        return False, "PyTorch not installed"
    except Exception as e:
        return False, f"Unexpected error: {e}"
