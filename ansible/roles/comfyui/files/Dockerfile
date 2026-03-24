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

# Install torchaudio (needed by WanVideoWrapper). This upgrades torch from NGC 2.7.0a0
# to stable 2.10.0+cu128 which has native Blackwell sm_120 support — verified working.
# Remove NGC's stale opencv (compiled for numpy 1.x) and its artifacts to avoid conflicts.
RUN pip uninstall -y opencv 2>/dev/null; \
    rm -rf /usr/local/lib/python3.12/dist-packages/cv2* && \
    pip install --no-cache-dir torchaudio opencv-python-headless

# Install ComfyUI requirements, filtering out torch ecosystem (already installed above)
RUN grep -viE "^torch(vision|audio)?([=>< ]|$)" requirements.txt > requirements_filtered.txt && \
    pip install --no-cache-dir -r requirements_filtered.txt

# Install gitpython for ComfyUI-Manager
RUN pip install --no-cache-dir gitpython

# Install ComfyUI Manager
RUN git clone https://github.com/ltdrdata/ComfyUI-Manager.git ${COMFYUI_DIR}/custom_nodes/ComfyUI-Manager

# Install custom nodes for video generation (Wan2.x)
RUN git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git ${COMFYUI_DIR}/custom_nodes/ComfyUI-WanVideoWrapper && \
    pip install --no-cache-dir -r ${COMFYUI_DIR}/custom_nodes/ComfyUI-WanVideoWrapper/requirements.txt

RUN git clone https://github.com/kijai/ComfyUI-KJNodes.git ${COMFYUI_DIR}/custom_nodes/ComfyUI-KJNodes && \
    pip install --no-cache-dir -r ${COMFYUI_DIR}/custom_nodes/ComfyUI-KJNodes/requirements.txt

# Face/identity nodes for EoBQ creative pipeline
RUN git clone https://github.com/Gourieff/ComfyUI-ReActor.git ${COMFYUI_DIR}/custom_nodes/ComfyUI-ReActor && \
    pip install --no-cache-dir -r ${COMFYUI_DIR}/custom_nodes/ComfyUI-ReActor/requirements.txt

RUN git clone https://github.com/balazik/ComfyUI-PuLID-Flux.git ${COMFYUI_DIR}/custom_nodes/ComfyUI-PuLID-Flux && \
    pip install --no-cache-dir -r ${COMFYUI_DIR}/custom_nodes/ComfyUI-PuLID-Flux/requirements.txt

RUN git clone https://github.com/cubiq/PuLID_ComfyUI.git ${COMFYUI_DIR}/custom_nodes/PuLID_ComfyUI && \
    pip install --no-cache-dir -r ${COMFYUI_DIR}/custom_nodes/PuLID_ComfyUI/requirements.txt

RUN git clone https://github.com/ltdrdata/ComfyUI-Impact-Pack.git ${COMFYUI_DIR}/custom_nodes/ComfyUI-Impact-Pack && \
    pip install --no-cache-dir -r ${COMFYUI_DIR}/custom_nodes/ComfyUI-Impact-Pack/requirements.txt

RUN git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus.git ${COMFYUI_DIR}/custom_nodes/ComfyUI_IPAdapter_plus

RUN git clone https://github.com/bytedance/InfiniteYou.git ${COMFYUI_DIR}/custom_nodes/ComfyUI_InfiniteYou && \
    pip install --no-cache-dir -r ${COMFYUI_DIR}/custom_nodes/ComfyUI_InfiniteYou/requirements.txt

EXPOSE 8188

CMD ["python3", "main.py", "--listen", "0.0.0.0", "--port", "8188"]
