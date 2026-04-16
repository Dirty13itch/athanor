---
name: drift-check
description: Run drift detection to verify system matches architectural decisions
---

Run the drift detection script to verify zero cloud spending, local-only fallbacks, and all infrastructure healthy:

```bash
bash /home/shaun/repos/athanor/scripts/drift-check.sh
```

If any checks fail, investigate and fix before continuing. Key principles:
- Zero Anthropic API spending (use Claude Max subscription via CLI)
- No subscription-CLI models in LiteLLM (use native CLIs: claude, codex, gemini, kimi)
- Local-only fallback chains
- All services must be healthy