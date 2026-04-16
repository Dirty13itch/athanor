Deployment safety hierarchy:

1. FOUNDRY (.244) is production. NEVER modify its running services without explicit user approval.
   - Read-only operations (SSH audit, log reading, nvidia-smi) are always allowed.
   - Config changes, service restarts, model swaps require approval.

2. WORKSHOP (.225) is staging. Changes allowed after testing on DEV.
   - Always keep the fallback model (5060Ti) running when swapping the primary (5090).

3. DEV is the sandbox. Anything goes here.

4. VAULT (.203) runs shared services (LiteLLM, LangFuse, databases).
   - LiteLLM config changes: always backup first (`cp config.yaml config.yaml.bak.$(date +%s)`).
   - Database operations: never drop without explicit approval.

5. Deploy via Ansible when playbooks exist. Manual SSH only for ad-hoc debugging.
