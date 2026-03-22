# DEV Node Rebuild Runbook

If DEV dies, rebuild in this order:

## 1. Base OS
- Ubuntu 24.04 LTS, kernel 6.17+
- NVIDIA driver (for 5060 Ti)
- Docker with nvidia-container-toolkit

## 2. User Setup
- Create user shaun, add to docker group
- Copy ~/.ssh/ from backup
- Copy ~/.secrets/ from backup (ALL API keys)

## 3. Core Services (systemd)
```bash
# Clone repo
git clone git@github.com:Dirty13itch/athanor.git ~/repos/athanor

# Create venvs for each service
for svc in gateway mind memory perception classifier governor; do
    cd ~/repos/athanor/services/$svc
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt  # if exists
done

# Install systemd units
sudo cp ~/repos/athanor/scripts/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now local-system-gateway local-system-mind local-system-memory local-system-perception athanor-classifier athanor-governor openfang
```

## 4. Docker Services
```bash
# Embedding + Reranker
docker run -d --name vllm-embedding --gpus all --restart unless-stopped ...
docker run -d --name vllm-reranker --gpus all --restart unless-stopped ...

# Open WebUI
docker run -d --name open-webui --restart unless-stopped -p 3080:8080 ...

# Arize Phoenix
docker run -d --name arize-phoenix --restart unless-stopped -p 6006:6006 ...
```

## 5. Shell Tools
```bash
# See Phase 6 of the plan: ~/.claude/plans/twinkling-dancing-pony.md
# Or just source the .bashrc from backup
```

## 6. CLI Tools
```bash
npm install -g @anthropic-ai/claude-code @openai/codex @github/copilot @google/gemini-cli @kilocode/cli @opencode-ai/opencode @composio/ao @biomejs/biome
pip install --user ruff basedpyright agentbudget
# See Phase 4 of the plan for full list
```

## 7. Verify
```bash
bash ~/repos/athanor/scripts/drift-check.sh  # Should be 37/37
```
