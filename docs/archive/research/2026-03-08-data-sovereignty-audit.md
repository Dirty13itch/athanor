# Data Sovereignty Audit

**Date:** 2026-03-08
**Auditor:** Claude (COO)
**Scope:** All 4 cluster nodes — verify zero unauthorized outbound telemetry

---

## Findings Summary

| Node | Outbound Connections | Telemetry Risk | Status |
|------|---------------------|----------------|--------|
| FOUNDRY (.244) | Zero non-cluster connections | **Fixed:** vLLM missing `VLLM_NO_USAGE_STATS=1` | ✅ Fixed in Ansible |
| WORKSHOP (.225) | Zero non-cluster connections | Same vLLM issue | ✅ Fixed in Ansible |
| VAULT (.203) | Docker bridge only (internal) | **Fixed:** LiteLLM missing `LITELLM_TELEMETRY=False` | ✅ Fixed in Ansible |
| DEV (.189) | Claude Code (Anthropic API) | Expected — dev tool | ⚠️ Documented |

## Detailed Audit

### FOUNDRY (.244)
- **Firewall:** nftables installed but inactive (empty ruleset). No UFW.
- **Outbound connections:** Zero non-local/non-cluster connections observed.
- **HF_HUB_OFFLINE=1:** ✅ Set in all vLLM containers (prevents model downloads/checks).
- **VLLM_NO_USAGE_STATS:** ❌ Was missing. vLLM sends anonymous usage stats by default. **Fixed** in `ansible/roles/vllm/templates/docker-compose.yml.j2`.
- **CUDA_DEVICE_ORDER=PCI_BUS_ID:** ✅ Set.
- **Containers:** 3 vLLM instances (reasoning, coding, creative), athanor-agents, gpu-orchestrator, qdrant, voice services, monitoring exporters.

### WORKSHOP (.225)
- **Firewall:** UFW active, default deny incoming / allow outgoing. Inbound: SSH, node_exporter, dcgm-exporter, vLLM, Open WebUI, Dashboard, ComfyUI, EoBQ.
- **Outbound connections:** Zero non-cluster connections.
- **Recommendation:** Consider restricting outbound to cluster-only via UFW egress rules.
- **Same vLLM fix applies.**

### VAULT (.203)
- **Outbound connections:** Docker bridge traffic only (container-to-container: miniflux↔postgresql, tdarr, cadvisor).
- **LiteLLM:** Routes all inference through local vLLM instances. No external API keys configured.
- **LITELLM_TELEMETRY:** ❌ Was missing. LiteLLM can send anonymous usage data. **Fixed** in Ansible.
- **LangFuse:** Self-hosted at :3030. No cloud sync.
- **Open WebUI:** Self-hosted at :3090. No cloud features enabled.
- **Miniflux:** Fetches RSS feeds from internet (expected — intelligence pipeline).
- **n8n:** Self-hosted at :5678. No cloud features.

### DEV (.189)
- **Claude Code:** Connects to Anthropic API (expected — primary dev tool).
- **Claude Code telemetry:** `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` NOT set in shell profile.
- **Recommendation:** Add to `~/.bashrc`.
- **Embedding/Reranker:** Local vLLM instances, no outbound.

## Remediation Applied

1. **vLLM telemetry disabled:** Added `VLLM_NO_USAGE_STATS=1` and `DO_NOT_TRACK=1` to `ansible/roles/vllm/templates/docker-compose.yml.j2`. Will take effect on next Ansible convergence or container rebuild.

2. **LiteLLM telemetry disabled:** Added `LITELLM_TELEMETRY=False` and `DO_NOT_TRACK=1` to `ansible/roles/vault-litellm/tasks/main.yml`.

3. **Pending:** Set `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` in DEV shell profile (non-blocking, dev tool).

## Allowed Outbound Connections

| Source | Destination | Purpose | Acceptable |
|--------|-------------|---------|------------|
| VAULT (miniflux) | Internet RSS feeds | Intelligence pipeline | ✅ Yes |
| VAULT (n8n) | Cluster services only | Workflow automation | ✅ Yes |
| DEV (Claude Code) | Anthropic API | Development tool | ✅ Yes |
| DEV (apt/pip) | Package repos | Software updates | ✅ Yes |
| All nodes | NTP servers | Time sync | ✅ Yes |

## Firewall Recommendations

1. **FOUNDRY:** Enable nftables with cluster-only egress (no internet needed for inference).
2. **WORKSHOP:** Add UFW egress rules restricting to 192.168.1.0/24 + DNS + NTP only.
3. **VAULT:** Consider restricting outbound to RSS feed domains + cluster + DNS/NTP.

---

*Last updated: 2026-03-08*
