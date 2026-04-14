# Promptfoo Pilot Agent Comparison

Small Promptfoo scaffold for bounded, cloud-safe pilot comparisons:

- `goose-vs-direct-cli.yaml`
- `openhands-vs-native-worker.yaml`
- `letta-vs-repo-native.yaml`

Non-Promptfoo benchmark scaffold:

- `agt-policy-bridge.yaml`

Shared pieces:

- `providers/agent_command_provider.py`: env-driven Promptfoo Python provider that launches an external agent command and passes the rendered prompt plus a JSON payload file.
- `prompts/bounded-cloud-safe-task.txt`: common prompt contract for read-only, cloud-safe tasks.
- `tests/bounded-cloud-safe.yaml`: four bounded pilot tasks shared by both pairwise configs.

Command wiring is now split between baked-in defaults we can verify locally and env-driven overrides for the lanes that still need them.

Built-in defaults:

- `Goose` uses `goose run --text "{prompt}" --no-session --quiet --output-format text --max-turns 1`
- `Direct CLI` uses `codex exec --skip-git-repo-check --json "{prompt}"`
- `Letta` uses `letta -p "{prompt}" --output-format text`
- `Repo-native context` uses `codex exec --skip-git-repo-check --json "{prompt}"`
- `Native Worker` uses `codex exec --skip-git-repo-check --json "{prompt}"`

Still env-driven:

- `PROMPTFOO_OPENHANDS_CMD`
- `PROMPTFOO_OPENHANDS_ARGS_JSON`

Supported argument placeholders:

- `{prompt}`
- `{prompt_file}`
- `{payload_file}`
- `{task_id}`
- `{provider_id}`

Example PowerShell wiring shape for the remaining env-driven lane:

```powershell
$env:PROMPTFOO_OPENHANDS_CMD = "openhands"
$env:PROMPTFOO_OPENHANDS_ARGS_JSON = "[\"run\", \"{prompt}\"]"
```

Run from repo root:

```powershell
npx promptfoo@latest eval -c evals/pilot-agent-compare/goose-vs-direct-cli.yaml
npx promptfoo@latest eval -c evals/pilot-agent-compare/openhands-vs-native-worker.yaml
npx promptfoo@latest eval -c evals/pilot-agent-compare/letta-vs-repo-native.yaml
```

Before treating any pilot as formal-eval-ready, run the source-safe preflight:

```powershell
python scripts/run_capability_pilot_formal_preflight.py
```

That report writes to `C:/Athanor/reports/truth-inventory/capability-pilot-formal-preflight.json` and is the contract that separates operator-smoke evidence from actual formal-eval readiness.

Once a run is preflight-ready, use the formal runner rather than ad hoc promptfoo commands:

```powershell
python scripts/run_capability_pilot_formal_eval.py --run-id goose-operator-shell-lane-eval-2026q2
```

The shared tasks are intentionally bounded: inline artifacts only, no live secrets, no external network dependency, and no destructive or stateful actions.

The Letta headless path also needs `LETTA_API_KEY` (or equivalent authenticated headless access) in the current local environment; local install alone is not enough to clear formal preflight.

The AGT pilot currently uses `agt-policy-bridge.yaml` as a benchmark-spec scaffold rather than a Promptfoo config because the narrow policy-bridge slice is still contract-driven and does not yet have a concrete runnable adapter. Its preflight also requires concrete fixture traces at:

- `C:/Athanor/evals/pilot-agent-compare/fixtures/agt-native-decision-trace.json`
- `C:/Athanor/evals/pilot-agent-compare/fixtures/agt-bridge-decision-trace.json`

Once valid fixtures exist, `scripts/run_capability_pilot_formal_eval.py` can materialize the native trace, bridge trace, diff summary, and rollback note as a benchmark-spec manual-review bundle without needing Promptfoo.
