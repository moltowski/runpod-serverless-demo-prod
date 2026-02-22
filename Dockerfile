# ==============================================================================
# RunPod Serverless ComfyUI-WAN - Config A (Stable)
# ==============================================================================
# Compatible: A100 80GB, A100 40GB, L40, RTX 4090
# PyTorch: 2.4.0 stable avec CUDA 12.4
# Testé: endpoint 48jzcfbsmucww8
# ==============================================================================

FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# CUDA environment
ENV CUDA_HOME=/usr/local/cuda
ENV PATH="${CUDA_HOME}/bin:${PATH}"
ENV LD_LIBRARY_PATH="${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}"

# PyTorch memory optimizations (safe defaults)
ENV PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

# System packages
RUN apt-get update && apt-get install -y \
    python3.10 python3.10-venv python3-pip \
    git wget curl ffmpeg unzip \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python environment
RUN python3.10 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Core dependencies - PyTorch STABLE cu124 (A100 compatible)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    torch==2.4.0 \
    torchvision==0.19.0 \
    torchaudio==2.4.0 \
    --index-url https://download.pytorch.org/whl/cu124

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

# Install ComfyUI
WORKDIR /ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git . && \
    pip install --no-cache-dir -r requirements.txt

# Create empty directories (will be replaced by symlinks at runtime by handler)
# IMPORTANT: Do NOT create /ComfyUI/temp here - handler creates it as a real dir
RUN mkdir -p /ComfyUI/models && \
    mkdir -p /ComfyUI/custom_nodes && \
    mkdir -p /ComfyUI/output

# Copy handlers
COPY handler.py /handler.py
COPY handler_debug.py /handler_debug.py
COPY handler_safe.py /handler_safe.py
COPY handler_final.py /handler_final.py
COPY utils.py /utils.py

# CRITICAL: Set Python unbuffered for logs
ENV PYTHONUNBUFFERED=1

# Expose ComfyUI port
EXPOSE 8188

# Start FINAL handler
CMD ["python3", "-u", "/handler_final.py"]
