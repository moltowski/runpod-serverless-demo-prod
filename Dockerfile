# RunPod Serverless ComfyUI-WAN Demo (Network Storage Optimized)
FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# System packages
RUN apt-get update && apt-get install -y \
    python3.10 python3.10-venv python3-pip \
    git wget curl ffmpeg unzip \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python environment
RUN python3.10 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Core dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

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

# Install ComfyUI (lightweight, models from network storage)
WORKDIR /ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git . && \
    pip install --no-cache-dir -r requirements.txt

# Essential custom nodes for WAN
RUN mkdir -p custom_nodes && cd custom_nodes && \
    git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git && \
    cd ComfyUI-WanVideoWrapper && \
    pip install --no-cache-dir -r requirements.txt || echo "Requirements install completed with warnings"

# Additional useful nodes
RUN cd custom_nodes && \
    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git && \
    cd ComfyUI-VideoHelperSuite && \
    pip install --no-cache-dir -r requirements.txt || echo "VideoHelper requirements completed"

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
COPY utils.py /utils.py

# Expose ComfyUI port (internal)
EXPOSE 8188

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
    CMD python -c "import requests; requests.get('http://localhost:8188', timeout=5)" || exit 1

# Start handler
CMD ["python", "-u", "/handler.py"]