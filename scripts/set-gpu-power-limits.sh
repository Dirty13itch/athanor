#!/bin/bash
# Set GPU power limits on Node 1
# Run this on every boot to maintain optimized power levels

# Wait for NVIDIA driver to initialize
sleep 10

# RTX 4090 - Slot 1
nvidia-smi -i 0 -pl 320

# RTX 5070 Ti - Slots 2-5
nvidia-smi -i 1 -pl 240
nvidia-smi -i 2 -pl 240
nvidia-smi -i 3 -pl 240
nvidia-smi -i 4 -pl 240

# Log results
echo "$(date): GPU power limits applied" >> /var/log/gpu-power-limits.log
nvidia-smi -q -d POWER | grep -E "GPU|Power Limit" >> /var/log/gpu-power-limits.log
