# Troubleshooting Guide

## Service Down?
```bash
# Quick health check (37 checks, should be 37/37)
bash ~/repos/athanor/scripts/drift-check.sh

# Restart a DEV service
sudo systemctl restart local-system-gateway
sudo systemctl restart local-system-mind
sudo systemctl restart local-system-memory
sudo systemctl restart athanor-classifier
sudo systemctl restart athanor-governor
sudo systemctl restart openfang

# Restart a Docker service on DEV
docker restart open-webui
docker restart vllm-embedding
docker restart vllm-reranker

# Restart vLLM on FOUNDRY
ssh foundry "docker restart vllm-coordinator"
ssh foundry "docker restart vllm-coder"

# Restart vLLM on WORKSHOP
ssh workshop "docker restart vllm-node2"
```

## LiteLLM Not Routing?
```bash
# Check LiteLLM health
LKEY=$(cat ~/.secrets/litellm-master-key)
curl -H "Authorization: Bearer $LKEY" http://192.168.1.203:4000/health

# Restart LiteLLM
ssh root@192.168.1.203 "docker restart litellm"

# Config location
ssh root@192.168.1.203 "cat /mnt/user/appdata/litellm/config.yaml"
```

## Model OOM?
- 4090 (24GB): Max ~13GB for weights (AWQ-4bit) + KV cache
- 5090 (32GB): Max ~18GB for weights (AWQ-4bit) + KV cache
- 5060 Ti (16GB): Use Ollama, not vLLM Docker (CUDA driver compat issue)
- TP=4 (64GB): Max ~40GB for weights + KV cache

## Open WebUI Shows No Models?
```bash
# Check container env
docker inspect open-webui --format={{range .Config.Env}}{{println .}}{{end}} | grep OPENAI

# Should show:
# OPENAI_API_BASE_URLS=http://192.168.1.203:4000/v1
# OPENAI_API_KEYS=sk-athanor-litellm-2026
```

## Governor Not Dispatching?
```bash
# Check governor health
curl http://localhost:8760/health | python3 -m json.tool

# Check logs
sudo journalctl -u athanor-governor -f

# Check SQLite DB
sqlite3 ~/repos/athanor/services/governor/governor.db "SELECT * FROM tasks"
```

## Classifier Says Everything Is Safe?
The classifier uses Qwen3Guard-Gen-0.6B with the chat template pipeline.
If it stops classifying correctly, restart:
```bash
sudo systemctl restart athanor-classifier
```

## SSH Aliases
```
ssh dev        # DEV (shaun@192.168.1.189)
ssh foundry    # FOUNDRY (athanor@192.168.1.244)
ssh workshop   # WORKSHOP (athanor@192.168.1.225)
ssh root@192.168.1.203  # VAULT (root only)
```
