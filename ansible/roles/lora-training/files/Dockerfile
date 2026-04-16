FROM pytorch/pytorch:2.6.0-cuda12.6-cudnn9-devel

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install kohya sd-scripts for Flux LoRA training
RUN pip install --no-cache-dir \
    accelerate \
    transformers \
    diffusers \
    safetensors \
    bitsandbytes \
    prodigyopt \
    lion-pytorch \
    dadaptation \
    wandb \
    toml \
    Pillow \
    numpy \
    scipy

# Clone sd-scripts (Flux support branch)
RUN git clone --depth 1 https://github.com/kohya-ss/sd-scripts.git /app/sd-scripts \
    && cd /app/sd-scripts && pip install --no-cache-dir -e .

WORKDIR /app/sd-scripts

ENTRYPOINT ["python3"]
