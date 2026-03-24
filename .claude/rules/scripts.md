---
paths:
  - "scripts/**"
---

# Script Conventions

- Always use bash strict mode: `set -euo pipefail`
- Include usage/help output (`-h` or `--help` flag)
- Scripts must be idempotent — safe to run multiple times
- Use descriptive variable names, not single letters
- Quote all variables: `"$var"` not `$var`
- Use `#!/usr/bin/env bash` shebang (not `/bin/bash`)
- Log to stderr, output to stdout: `echo "info" >&2`
- Exit codes: 0=success, 1=general error, 2=usage error
- SSH to nodes: use config aliases (`node1`, `node2`), not raw IPs
- VAULT SSH: always use `python3 scripts/vault-ssh.py`
- Naming: lowercase, hyphen-separated: `build-profile.sh`, `index-knowledge.py`
