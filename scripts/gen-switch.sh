#!/bin/bash
# Switch between ComfyUI (images) and Wan2GP (video)
# Both need the GPU exclusively

case "$1" in
  comfyui|images|img)
    echo "Stopping Wan2GP..."
    sudo systemctl stop wan2gp 2>/dev/null
    sleep 2
    echo "Starting ComfyUI on :8188..."
    sudo systemctl start comfyui
    sleep 3
    echo "ComfyUI is running: http://192.168.1.189:8188"
    ;;
  wan2gp|video|vid)
    echo "Stopping ComfyUI..."
    sudo systemctl stop comfyui
    sleep 2
    echo "Starting Wan2GP on :7860..."
    sudo systemctl start wan2gp
    sleep 5
    echo "Wan2GP is running: http://192.168.1.189:7860"
    ;;
  status)
    echo "=== ComfyUI ==="
    systemctl is-active comfyui
    echo "=== Wan2GP ==="
    systemctl is-active wan2gp
    echo "=== GPU ==="
    nvidia-smi --query-gpu=name,memory.used,memory.free --format=csv,noheader
    ;;
  *)
    echo "Usage: gen-switch.sh [comfyui|wan2gp|status]"
    echo "  comfyui/images/img  - Image generation (FLUX, SDXL, Z-Image)"
    echo "  wan2gp/video/vid    - Video generation (Wan 2.2, HunyuanVideo)"
    echo "  status              - Check which service is running"
    ;;
esac
