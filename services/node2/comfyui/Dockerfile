FROM nvcr.io/nvidia/pytorch:25.02-py3

ENV DEBIAN_FRONTEND=noninteractive
ENV COMFYUI_DIR=/opt/ComfyUI

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Clone ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git ${COMFYUI_DIR}

WORKDIR ${COMFYUI_DIR}

# Install ComfyUI requirements BUT preserve NGC PyTorch (which has Blackwell sm_120 support).
# Only filter out exact torch, torchvision, torchaudio (not torchsde etc.)
RUN grep -viE "^torch(vision|audio)?([=>< ]|$)" requirements.txt > requirements_filtered.txt && \
    pip install --no-cache-dir -r requirements_filtered.txt

# Install gitpython for ComfyUI-Manager
RUN pip install --no-cache-dir gitpython

# Install ComfyUI Manager
RUN git clone https://github.com/ltdrdata/ComfyUI-Manager.git ${COMFYUI_DIR}/custom_nodes/ComfyUI-Manager

EXPOSE 8188

CMD ["python3", "main.py", "--listen", "0.0.0.0", "--port", "8188"]
