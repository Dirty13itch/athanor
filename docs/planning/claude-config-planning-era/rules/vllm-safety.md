When writing or modifying vLLM serve commands, Ansible vars, or systemd units for Qwen3.5 models:

- ALWAYS include `--tool-call-parser qwen3_coder` (Qwen3.5 uses XML format, not hermes)
- ALWAYS include `--kv-cache-dtype auto` (FP8 KV cache silently corrupts GDN layers)
- ALWAYS include `--max-num-batched-tokens 2096` (required for hybrid attention block size)
- ALWAYS include `--enable-auto-tool-choice` when tool calling is needed
- NEVER use `--kv-cache-dtype fp8` with any Qwen3.5 model
- For MoE models (35B-A3B), expect ~22GB VRAM for AWQ 4-bit
- For dense models (27B), expect ~27GB for FP8
- First cold start will spike VRAM due to Triton autotuner — persist ~/.cache/triton
