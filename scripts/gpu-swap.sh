#!/usr/bin/env bash
# GPU Time-Share Manager for Workshop 5090
# Swaps between vLLM Worker and ComfyUI on GPU 0
# Usage: gpu-swap.sh [creative|inference|status]

set -euo pipefail

VLLM_COMPOSE="/opt/athanor/vllm-node2/docker-compose.yml"
COMFYUI_COMPOSE="/opt/athanor/comfyui/docker-compose.yml"

status() {
    local vllm_running comfyui_running
    vllm_running=$(docker inspect -f "{{.State.Running}}" vllm-node2 2>/dev/null || echo "false")
    comfyui_running=$(docker inspect -f "{{.State.Running}}" comfyui 2>/dev/null || echo "false")
    
    if [ "$vllm_running" = "true" ]; then
        echo "MODE: inference"
        echo "GPU0: vLLM Worker (Qwen3.5-35B-A3B-AWQ)"
    elif [ "$comfyui_running" = "true" ]; then
        echo "MODE: creative"
        echo "GPU0: ComfyUI (Flux + PuLID)"
    else
        echo "MODE: idle"
        echo "GPU0: nothing running"
    fi
    
    # Always show vision status
    local vision_running
    vision_running=$(docker inspect -f "{{.State.Running}}" vllm-vision 2>/dev/null || echo "false")
    echo "GPU1: vLLM Vision ($( [ "$vision_running" = "true" ] && echo "running" || echo "stopped" ))"
}

swap_to_creative() {
    echo "=== Swapping GPU 0 to Creative Mode ==="
    
    # Stop vLLM worker
    if docker inspect -f "{{.State.Running}}" vllm-node2 2>/dev/null | grep -q true; then
        echo "Stopping vLLM worker..."
        cd "$(dirname "$VLLM_COMPOSE")" && docker compose stop vllm
        echo "vLLM worker stopped."
    fi
    
    # Start ComfyUI
    echo "Starting ComfyUI on GPU 0 (5090)..."
    cd "$(dirname "$COMFYUI_COMPOSE")" && docker compose up -d comfyui
    
    # Wait for ComfyUI to be ready
    echo "Waiting for ComfyUI..."
    for i in $(seq 1 30); do
        if curl -s --max-time 2 http://localhost:8188/system_stats > /dev/null 2>&1; then
            echo "ComfyUI ready on :8188"
            status
            exit 0
        fi
        sleep 2
    done
    echo "WARNING: ComfyUI did not become ready within 60s"
    status
}

swap_to_inference() {
    echo "=== Swapping GPU 0 to Inference Mode ==="
    
    # Stop ComfyUI
    if docker inspect -f "{{.State.Running}}" comfyui 2>/dev/null | grep -q true; then
        echo "Stopping ComfyUI..."
        cd "$(dirname "$COMFYUI_COMPOSE")" && docker compose stop comfyui
        echo "ComfyUI stopped."
    fi
    
    # Start vLLM worker
    echo "Starting vLLM worker on GPU 0 (5090)..."
    cd "$(dirname "$VLLM_COMPOSE")" && docker compose up -d vllm
    
    # Wait for vLLM to be ready
    echo "Waiting for vLLM worker..."
    for i in $(seq 1 60); do
        if curl -s --max-time 2 http://localhost:8000/health > /dev/null 2>&1; then
            echo "vLLM worker ready on :8000"
            status
            exit 0
        fi
        sleep 3
    done
    echo "WARNING: vLLM worker did not become ready within 180s (first Triton compile takes ~90s)"
    status
}

case "${1:-status}" in
    creative|comfyui|art)
        swap_to_creative
        ;;
    inference|vllm|worker)
        swap_to_inference
        ;;
    status|info)
        status
        ;;
    *)
        echo "Usage: gpu-swap.sh [creative|inference|status]"
        echo "  creative  — Stop vLLM worker, start ComfyUI on 5090"
        echo "  inference — Stop ComfyUI, start vLLM worker on 5090"
        echo "  status    — Show current GPU allocation"
        exit 1
        ;;
esac
