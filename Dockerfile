# RunPod Serverless ComfyUI-WAN Demo (RTX 5090 Compatible)
# Using CUDA 12.4 (latest available that supports RTX 5090)
FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# RTX 5090 optimizations
ENV PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True,max_split_size_mb:512
ENV TORCH_ALLOW_TF32_CUBLAS_OVERRIDE=0
ENV CUDA_LAUNCH_BLOCKING=0

# System packages
RUN apt-get update && apt-get install -y \
    python3.10 python3.10-venv python3-pip \
    git wget curl ffmpeg unzip \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python environment
RUN python3.10 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Core dependencies - PyTorch 2.4+ with CUDA 12.4
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch==2.4.0 torchvision==0.19.0 torchaudio==2.4.0 --index-url https://download.pytorch.org/whl/cu124

# RunPod SDK and essential packages
RUN pip install --no-cache-dir \
    runpod>=1.7.0 \
    requests \
    pillow \
    numpy \
    opencv-python \
    huggingface_hub \
    safetensors \
    accelerate \
    transformers

# Install ComfyUI (latest stable)
WORKDIR /ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git . && \
    pip install --no-cache-dir -r requirements.txt

# Create custom_nodes directory but DON'T install WAN nodes yet
# (they require cu130 which doesn't exist)
RUN mkdir -p custom_nodes

# Create symlinks to network storage (will be mounted at /workspace)
RUN mkdir -p /ComfyUI/models && \
    ln -sf /workspace/models/checkpoints /ComfyUI/models/checkpoints && \
    ln -sf /workspace/models/loras /ComfyUI/models/loras && \
    ln -sf /workspace/models/embeddings /ComfyUI/models/embeddings && \
    ln -sf /workspace/models/upscale_models /ComfyUI/models/upscale_models && \
    ln -sf /workspace/workflows /ComfyUI/workflows && \
    mkdir -p /ComfyUI/output && \
    ln -sf /workspace/temp /ComfyUI/temp

# Copy handler
COPY handler.py /handler.py
COPY utils.py /utils.py 2>/dev/null || true

# Expose ComfyUI port (internal)
EXPOSE 8188

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
    CMD python -c "import requests; requests.get('http://localhost:8188', timeout=5)" || exit 1

# Start handler
CMD ["python", "-u", "/handler.py"]
