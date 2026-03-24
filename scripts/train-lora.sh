#!/usr/bin/env bash
# Flux LoRA training pipeline for EoBQ queen character consistency.
#
# Usage:
#   train-lora.sh <performer_name> [trigger_word] [steps]
#
# Examples:
#   train-lora.sh "Ava Addams" ohwx_ava 1500
#   train-lora.sh "Mia Malkova" ohwx_mia
#
# Prerequisites:
#   - Ansible role deployed: ansible-playbook playbooks/workshop.yml --tags lora-training
#   - Stash running on VAULT:9999 with performer photos
#   - Workshop 5090 available (will stop vLLM worker during training)

set -euo pipefail

PERFORMER="${1:?Usage: train-lora.sh <performer_name> [trigger_word] [steps]}"
TRIGGER="${2:-ohwx}"
STEPS="${3:-1500}"

WORKSHOP="workshop"
TRAINING_DIR="/opt/athanor/lora-training"
DATASETS_DIR="/data/training/datasets"
OUTPUT_DIR="/data/training/output"
LORAS_DIR="/mnt/vault/models/comfyui/loras"

SAFE_NAME=$(echo "$PERFORMER" | tr '[:upper:]' '[:lower:]' | tr ' ' '_')

echo "=== LoRA Training Pipeline ===" >&2
echo "Performer: $PERFORMER" >&2
echo "Trigger:   $TRIGGER" >&2
echo "Steps:     $STEPS" >&2
echo "" >&2

# 1. Prepare dataset from Stash
echo "[1/5] Preparing dataset from Stash..." >&2
ssh "$WORKSHOP" "cd $TRAINING_DIR && python3 prepare-dataset.py '$PERFORMER' --trigger '$TRIGGER' --repeats 20"

# 2. Stop vLLM worker to free 5090 VRAM
echo "[2/5] Stopping vLLM worker to free GPU..." >&2
ssh "$WORKSHOP" "docker stop vllm-worker 2>/dev/null || true"
sleep 3

# 3. Run training
echo "[3/5] Starting LoRA training ($STEPS steps)..." >&2
ssh "$WORKSHOP" "cd $TRAINING_DIR && docker compose --profile training run --rm \
  -e MAX_TRAIN_STEPS=$STEPS \
  lora-training"

# 4. Copy output to ComfyUI loras directory
echo "[4/5] Copying trained LoRA to ComfyUI..." >&2
ssh "$WORKSHOP" "cp '$OUTPUT_DIR/${TRIGGER}.safetensors' '$LORAS_DIR/' 2>/dev/null || echo 'LoRA output not found at expected path'"

# 5. Restart vLLM worker
echo "[5/5] Restarting vLLM worker..." >&2
ssh "$WORKSHOP" "docker start vllm-worker"

echo "" >&2
echo "=== Training Complete ===" >&2
echo "LoRA: $LORAS_DIR/${TRIGGER}.safetensors" >&2
echo "Use in ComfyUI with trigger word: $TRIGGER" >&2
