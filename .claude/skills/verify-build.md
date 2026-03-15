# Verify Build

Run type-checking and validation for the current or specified project.

## Detection

Detect project type from cwd or argument:

| Indicator | Type | Check |
|-----------|------|-------|
| `tsconfig.json` present | TypeScript | `npx tsc --noEmit` |
| `.py` files present | Python | `python3 -m py_compile` per file |
| `tests/` or `test/` dir | Python tests | `pytest -x --tb=short` |
| `ansible/` dir | Ansible | `ansible-lint playbooks/` + YAML validation |

## TypeScript

```bash
# Dashboard
cd /home/shaun/repos/athanor/projects/dashboard && npx tsc --noEmit

# EoBQ
cd /home/shaun/repos/athanor/projects/eoq && npx tsc --noEmit
```

## Python

```bash
# Compile check specific files
python3 -m py_compile agents/general_assistant.py

# Compile check all agent files
find agents/ -name '*.py' -exec python3 -m py_compile {} \;

# Run tests if they exist
[ -d tests/ ] && pytest tests/ -x --tb=short
```

## Ansible

```bash
# Lint playbooks
ansible-lint playbooks/ 2>&1 | head -20

# YAML validation
python3 -c "import yaml; yaml.safe_load(open('ansible/roles/vllm/defaults/main.yml'))"
```

## Procedure

1. Detect all project types present in cwd
2. Run all applicable checks
3. Report first 10 errors for each type
4. Return clear PASS/FAIL per project type
