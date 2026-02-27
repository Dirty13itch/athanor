# Autonomous Local Coding Agent: Options Analysis

**Date**: 2026-02-26
**Status**: Research complete
**Purpose**: Evaluate options for running a 24/7 autonomous coding agent on Athanor hardware with zero API costs
**Related**: `2026-02-16-tool-calling-coding-models.md` (model benchmarks), `2026-02-16-model-stack-synthesis.md` (GPU allocation)

---

## Context

Athanor has 88 GB of NVIDIA VRAM across 7 GPUs, with vLLM serving Qwen3-32B-AWQ on Node 1. The goal is a coding agent that runs headless 24/7, picks up tasks from a queue, generates/reviews/tests code, and writes output to a staging directory for human review. Zero API cost -- local inference only.

### Hardware Available

| Node | GPUs | VRAM | vLLM Port | CPU | RAM |
|------|------|------|-----------|-----|-----|
| Node 1 (Foundry) | 4x 5070 Ti + 4090 | 88 GB | :8000 | EPYC 56C | 224 GB |
| Node 2 (Workshop) | 5090 + 5060 Ti | 48 GB | :8000 | TR 24C | 128 GB |

### Requirements

1. Use OpenAI-compatible API (vLLM at `http://192.168.1.244:8000/v1`)
2. Run headless/daemon mode 24/7 without human interaction
3. Docker deployment preferred
4. Produce useful output with 27-32B class models
5. Active community and maintenance

---

## Option 1: Goose (Block)

**Repository**: [github.com/block/goose](https://github.com/block/goose)
**License**: Apache 2.0
**Stars**: 30,000+
**Language**: Rust (core) + TypeScript (extensions)
**Last activity**: Active (110+ releases, 350+ contributors, donated to Linux Foundation Agentic AI Foundation Dec 2025)

### Local LLM Support

Goose supports OpenAI-compatible endpoints via the built-in OpenAI provider:

```bash
export GOOSE_PROVIDER=openai
export OPENAI_HOST=http://192.168.1.244:8000
export OPENAI_API_KEY=dummy
export GOOSE_MODEL=Qwen/Qwen3-32B-AWQ
```

Also supports Ollama directly, and custom providers via JSON config files in `~/.config/goose/custom_providers/`.

Source: [Goose Provider Configuration](https://block.github.io/goose/docs/getting-started/providers/)

### Headless / Daemon Mode

Goose has a dedicated headless mode designed for automation:

```bash
# One-shot task
goose run -t "Write unit tests for auth.py"

# Recipe-based (reusable YAML workflow)
goose run --recipe code-review.yaml --params target_directory=./src

# Cron scheduling
0 2 * * * /usr/local/bin/goose run --no-session -t "Run security audit"
```

Recipes support parameters, retry logic, sub-recipes, and extension configuration. Subagents spawn isolated sessions with a TasksManager for parallel work.

Source: [Goose Headless Mode](https://block.github.io/goose/docs/tutorials/headless-goose/), [Goose Roadmap](https://github.com/block/goose/discussions/3319)

### Docker Support

Yes. Docker Compose support, MCP server integration, Docker Model Runner for local models.

Source: [Docker + Goose](https://www.docker.com/blog/building-ai-agents-with-goose-and-docker/)

### Critical Issue: vLLM Tool Calling

**There is an unresolved issue with Goose failing to execute tool calls on custom vLLM endpoints.** The model sees and describes available tools but cannot invoke them. Tested with Qwen3 and IBM Granite on vLLM. The same endpoint works correctly with `mcphost`, indicating a Goose-specific integration problem.

Status: Unresolved as of January 2026. Maintainer attributed it to "model related" issues without confirmation.

Source: [GitHub Discussion #5914](https://github.com/block/goose/discussions/5914), [Issue #3857](https://github.com/block/goose/issues/3857)

### Assessment

| Criterion | Score | Notes |
|-----------|-------|-------|
| OpenAI-compatible API | 8/10 | Works in principle; vLLM tool calling bug is blocking |
| Headless/daemon 24/7 | 9/10 | Best-in-class headless mode, recipes, cron scheduling |
| Docker deployment | 8/10 | Docker Compose supported |
| 32B model quality | ?/10 | Cannot evaluate -- tool calling broken on vLLM |
| Community/maturity | 9/10 | 30K stars, Linux Foundation, Block backing |
| **Overall** | **7/10** | **Excellent framework, blocked by vLLM tool calling bug** |

---

## Option 2: Aider

**Repository**: [github.com/Aider-AI/aider](https://github.com/Aider-AI/aider)
**License**: Apache 2.0
**Stars**: 30,000+
**Language**: Python
**Last activity**: Active (frequent releases)

### Local LLM Support

Aider supports any OpenAI-compatible endpoint:

```bash
aider --openai-api-base http://192.168.1.244:8000/v1 \
      --openai-api-key dummy \
      --model openai/Qwen3-32B-AWQ \
      --message "Add error handling to utils.py" \
      utils.py
```

Also supports Ollama, and has a comprehensive model leaderboard tracking quality with different backends.

Source: [Aider LLM Docs](https://aider.chat/docs/llms.html), [Aider Other LLMs](https://aider.chat/docs/llms/other.html)

### Headless / Daemon Mode

Aider is fundamentally a pair-programmer, not an autonomous agent. Headless operation is limited:

```bash
# Single-shot mode (runs one task, exits)
aider --message "add docstrings to all functions" --yes myfile.py

# Batch via shell script
for FILE in *.py; do
    aider --message "add type hints" --yes $FILE
done

# Python API (unsupported, may break)
from aider.coders import Coder
from aider.models import Model
model = Model("openai/Qwen3-32B-AWQ")
coder = Coder.create(main_model=model, fnames=["app.py"])
coder.run("add error handling")
```

**There is no daemon mode.** Each `--message` invocation runs one task and exits. The `--yes-always` flag has a known bug where shell commands don't execute. There is no task queue, no scheduling, no persistent worker.

Source: [Aider Scripting](https://aider.chat/docs/scripting.html), [Issue #3903](https://github.com/Aider-AI/aider/issues/3903)

### Docker Support

No official Docker image. Community containerization possible but not maintained.

### Assessment

| Criterion | Score | Notes |
|-----------|-------|-------|
| OpenAI-compatible API | 9/10 | Excellent, well-documented |
| Headless/daemon 24/7 | 3/10 | One-shot only, no daemon, no queue, --yes-always buggy |
| Docker deployment | 3/10 | No official support |
| 32B model quality | 8/10 | Qwen2.5-Coder-32B scores 73.7 on Aider benchmark |
| Community/maturity | 9/10 | Mature, well-maintained, excellent leaderboard |
| **Overall** | **5/10** | **Great tool, wrong architecture -- designed for human interaction** |

---

## Option 3: OpenHands (formerly OpenDevin)

**Repository**: [github.com/OpenHands/OpenHands](https://github.com/OpenHands/OpenHands)
**License**: MIT
**Stars**: 38,800+
**Language**: Python + TypeScript
**Last activity**: Very active (v1.4 as of Feb 2026)

### Local LLM Support

OpenHands has explicit documentation for vLLM:

```bash
# Start vLLM
vllm serve Qwen/Qwen3-Coder-30B-A3B-Instruct \
  --host 0.0.0.0 --port 8000 --api-key mykey --tensor-parallel-size 4

# Configure OpenHands
LLM_MODEL="openai/Qwen3-32B-AWQ"
LLM_API_BASE="http://host.docker.internal:8000/v1"
LLM_API_KEY="mykey"
```

Recommended models: Qwen3-Coder-30B-A3B, Devstral Small 2 (24B). Published their own fine-tuned model: OpenHands-LM-32B (based on Qwen2.5-Coder-32B, 37.2% SWE-bench Verified).

Source: [OpenHands Local LLMs](https://docs.openhands.dev/openhands/usage/llms/local-llms), [OpenHands-LM-32B](https://openhands.dev/blog/introducing-openhands-lm-32b-a-strong-open-coding-agent-model)

### Headless / Daemon Mode

OpenHands supports headless CLI execution:

```bash
# Headless single task
openhands --headless -t "Write unit tests for auth.py"

# With JSON output
openhands --headless --json -t "Create a Flask app"

# Environment-based configuration
export LLM_MODEL="openai/Qwen3-32B-AWQ"
export LLM_API_BASE="http://192.168.1.244:8000/v1"
export LLM_API_KEY="dummy"
docker run --network host -v /workspace:/workspace openhands \
  --headless -t "Fix bug in parser.py"
```

Python SDK in development (as of Aug 2025) to unify configuration across UI, CLI, headless, and programmatic use.

**Known issues**: Headless mode has had bugs with endless loops (agent keeps saying "continue" without finishing), and earlier versions would stop to ask for user input even in headless mode. Both issues have PRs addressing them.

Source: [OpenHands CLI](https://github.com/OpenHands/OpenHands-CLI), [Issue #5535](https://github.com/OpenHands/OpenHands/issues/5535), [PR #5879](https://github.com/OpenHands/OpenHands/pull/5879)

### Docker Support

Docker is the primary deployment method. OpenHands runs a sandboxed Docker container for code execution -- it's Docker-in-Docker by design. This provides strong isolation but adds overhead.

### Critical Limitation

The documentation explicitly warns: **"When using a Local LLM, OpenHands may have limited functionality."** This is because the agent scaffold assumes frontier-model-level reasoning for multi-step planning. With 32B models, the agent may fail on complex multi-turn tasks.

### Assessment

| Criterion | Score | Notes |
|-----------|-------|-------|
| OpenAI-compatible API | 9/10 | Explicit vLLM docs, well-tested |
| Headless/daemon 24/7 | 6/10 | Headless mode exists but has reliability issues |
| Docker deployment | 10/10 | Docker-native, sandboxed execution |
| 32B model quality | 5/10 | "Limited functionality" with local models, 37.2% SWE-bench |
| Community/maturity | 9/10 | 38K stars, very active, Python SDK coming |
| **Overall** | **6/10** | **Strongest sandboxing, but local model quality concerns and headless bugs** |

---

## Option 4: SWE-agent / mini-swe-agent

**Repository**: [github.com/SWE-agent/SWE-agent](https://github.com/SWE-agent/SWE-agent) (maintenance mode), [github.com/SWE-agent/mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) (active)
**License**: MIT
**Stars**: SWE-agent 14K+, mini-swe-agent growing
**Language**: Python
**Origin**: Princeton / Stanford

### Critical Status Update

**SWE-agent (full) is in maintenance-only mode.** The team recommends migration to **mini-swe-agent**, a 100-line Python agent that scores >74% on SWE-bench Verified (with frontier models).

### Local LLM Support

Both use litellm, which supports all OpenAI-compatible endpoints:

```yaml
# mini-swe-agent config
model:
  name: openai/Qwen3-32B-AWQ
  api_base: http://192.168.1.244:8000/v1
  api_key: dummy
```

If the model doesn't support function calling, a `thought_action` parser can be used as fallback.

Source: [mini-swe-agent Local Models](https://mini-swe-agent.com/latest/models/local_models/), [SWE-agent Models](https://swe-agent.com/latest/installation/keys/)

### Headless / Batch Mode

SWE-agent has a dedicated batch mode for parallel processing:

```bash
sweagent run-batch \
    --config config/default.yaml \
    --agent.model.name openai/Qwen3-32B-AWQ \
    --num_workers 3 \
    --instances.type file \
    --instances.path tasks.jsonl
```

However, this is designed for **SWE-bench evaluation** (GitHub issue -> patch format), not general-purpose coding task queues.

Source: [SWE-agent Batch Mode](https://swe-agent.com/latest/usage/batch_mode/)

### Docker Support

Yes, Docker sandbox for code execution. Supports Docker, Podman, Singularity, Bubblewrap.

### Assessment

| Criterion | Score | Notes |
|-----------|-------|-------|
| OpenAI-compatible API | 8/10 | Via litellm, well-supported |
| Headless/daemon 24/7 | 5/10 | Batch mode exists but SWE-bench-focused, not general daemon |
| Docker deployment | 8/10 | Multiple sandbox options |
| 32B model quality | 6/10 | SWE-agent-LM-32B showed big improvements; depends on fine-tune |
| Community/maturity | 7/10 | SWE-agent in maintenance, mini-swe-agent is very new |
| **Overall** | **5/10** | **Academic-grade but too SWE-bench-specific for general 24/7 operation** |

---

## Option 5: Devon (Entropy Research)

**Repository**: [github.com/entropy-research/Devon](https://github.com/entropy-research/Devon)
**License**: Apache 2.0
**Stars**: ~800
**Language**: Python

### Assessment: Skip

Devon appears to be abandoned or very low activity. ~800 GitHub stars, minimal recent updates, unclear local model support, no Docker deployment documentation, no headless mode. Not a viable candidate for 24/7 autonomous operation.

| **Overall** | **2/10** | **Appears abandoned, insufficient for production use** |

---

## Option 6: Our Existing coding-agent (Athanor)

**Location**: `projects/agents/src/athanor_agents/agents/coding.py`
**Stack**: LangGraph + LangChain + FastAPI
**Deployment**: Node 1:9000, Docker Compose
**Status**: Running, 9 tools, integrated with Redis task queue

### Current Capabilities

- **Tools**: `read_file`, `write_file`, `list_directory`, `search_files`, `run_command`, `generate_code`, `review_code`, `explain_code`, `transform_code`
- **Task Engine**: Redis-backed queue, 5s poll, max 2 concurrent, auto-retry, step logging, 10-min timeout
- **Scheduler**: Runs on schedule (configurable intervals)
- **Context**: Qdrant RAG injection (preferences, activity, knowledge, goals)
- **Output**: Writes to `/output/` staging directory (read-only `/workspace/`)

### What It Lacks vs. Dedicated Agent Frameworks

1. **No sandboxed execution** -- `run_command` executes directly, no Docker isolation
2. **Limited autonomous loop** -- Relies on LLM's multi-turn reasoning, no explicit plan-execute-verify cycle
3. **No git integration** -- Doesn't commit, branch, or create PRs
4. **No test discovery/execution framework** -- Can run `pytest` via `run_command` but no structured test feedback
5. **No diff/patch generation** -- Writes full files, not surgical edits
6. **10-minute timeout** -- Hard limit on task duration
7. **No file watching or change detection** -- Passive queue consumer only

### What It Has That Others Don't

1. **Already deployed and integrated** with the full Athanor stack
2. **Understands the codebase** via Qdrant knowledge base (2220 chunks)
3. **Full control** -- Python, hackable, no external dependencies
4. **Task delegation** -- Can delegate to other agents (media, home, etc.)
5. **Activity logging** and GWT workspace integration
6. **Zero additional deployment work**

### Assessment

| Criterion | Score | Notes |
|-----------|-------|-------|
| OpenAI-compatible API | 10/10 | Uses LiteLLM proxy, already configured |
| Headless/daemon 24/7 | 7/10 | Task engine runs 24/7, but limited sophistication |
| Docker deployment | 10/10 | Already deployed |
| 32B model quality | 6/10 | Depends on model; Qwen3-32B adequate for simpler tasks |
| Community/maturity | 4/10 | Custom code, one-person maintenance |
| **Overall** | **7/10** | **Already running, needs enhancement not replacement** |

---

## Model Analysis: What to Run

The model choice matters more than the agent framework. A mediocre agent with a great model outperforms a great agent with a mediocre model.

### Current and Upcoming Options

| Model | Params | SWE-bench Verified | LiveCodeBench | VRAM (AWQ/Q4) | Fits On | Status |
|-------|--------|-------------------|---------------|---------------|---------|--------|
| **Qwen3-32B-AWQ** (current) | 32B dense | N/A (est. 40-50%) | 70.7 | ~19 GB | 4x 5070 Ti TP=4 | Running |
| **Qwen3.5-27B** | 27B dense | **72.4%** | **80.7** | ~16 GB (AWQ) | Single 5070 Ti or 5090 | Released Feb 24, 2026 |
| **Qwen3-Coder-30B-A3B** | 30B MoE (3B active) | 50.3% | N/A | ~19 GB | Single 4090 | Available |
| **Qwen3-Coder-Next** | 80B MoE (3B active) | 70.6% | N/A | ~46 GB (Q4) | 4x 5070 Ti TP=4 (tight) | Available |
| **OpenHands-LM-32B** | 32B dense | 37.2% | N/A | ~19 GB | 4x 5070 Ti TP=4 | Available |
| **Devstral Small 2** | 24B dense | 46.8% | N/A | ~14 GB | Single 5070 Ti | Available |

### Recommendation: Qwen3.5-27B

**Qwen3.5-27B is the clear winner for autonomous coding.** At 72.4% SWE-bench Verified, it:

- Matches GPT-5-mini on SWE-bench
- Achieves LiveCodeBench 80.7 (best in its weight class)
- Is a dense 27B model (no MoE complexity, predictable performance)
- Fits on a **single RTX 5070 Ti** at AWQ (~16 GB) or comfortably on RTX 5090
- Has a 262K context window (massive for codebase understanding)
- Was released February 24, 2026 -- it is current
- Supports IFEval 95.0 and IFBench 76.5 (excellent instruction following)

The jump from Qwen3-32B (est. 40-50% SWE-bench) to Qwen3.5-27B (72.4% SWE-bench) is transformative. This is the difference between "agent makes frequent mistakes" and "agent resolves most GitHub issues correctly."

**Deployment plan:**
```bash
# Download AWQ variant when available
huggingface-cli download Qwen/Qwen3.5-27B-AWQ

# Serve on Node 1 (single 5070 Ti, GPU 1)
vllm serve Qwen/Qwen3.5-27B-AWQ --port 8001 \
  --quantization awq --max-model-len 32768 \
  --enable-auto-tool-choice --tool-call-parser hermes \
  --gpu-memory-utilization 0.90
```

This leaves the TP=4 5070 Ti group free for general inference (Qwen3-32B) and dedicates a single GPU to the coding agent.

Sources: [Qwen3.5 Blog](https://qwen.ai/blog?id=qwen3.5), [Qwen3.5-27B Benchmarks](https://www.digitalapplied.com/blog/qwen-3-5-medium-model-series-benchmarks-pricing-guide), [AwesomeAgents Qwen3.5-27B](https://awesomeagents.ai/models/qwen-3-5-27b/)

---

## Comparison Matrix

| Criterion | Goose | Aider | OpenHands | SWE-agent | Devon | Our Agent |
|-----------|-------|-------|-----------|-----------|-------|-----------|
| OpenAI-compat API | 8 | 9 | 9 | 8 | ? | 10 |
| Headless 24/7 daemon | **9** | 3 | 6 | 5 | 2 | 7 |
| Docker deployment | 8 | 3 | **10** | 8 | 2 | **10** |
| 32B model quality | ? | 8 | 5 | 6 | ? | 6 |
| Sandboxed execution | 6 | 5 | **10** | 8 | ? | 2 |
| Git integration | 7 | **10** | 8 | 8 | 5 | 2 |
| Task queue / scheduling | **8** | 1 | 3 | 5 | 1 | **8** |
| Codebase knowledge | 3 | 5 | 4 | 3 | 3 | **9** |
| Customizability | 5 | 6 | 7 | 8 | 5 | **10** |
| Community / maintenance | **9** | **9** | **9** | 7 | 2 | 4 |
| **Total** | **63** | **59** | **71** | **66** | ~22 | **68** |

---

## Recommendation

### Short Term (Now): Enhance Our Existing coding-agent

The highest-value, lowest-risk path. Our agent is already deployed, integrated with the task queue, and understands the Athanor codebase. The enhancements needed:

1. **Upgrade model to Qwen3.5-27B-AWQ** -- This alone transforms capability from ~45% to 72% SWE-bench quality. Single GPU deployment, no TP needed.

2. **Add sandboxed execution** -- Wrap `run_command` in a Docker container (use the existing Docker socket). Prevent the agent from modifying anything outside `/output/`.

3. **Add git integration** -- Branch creation, commit, diff generation. The agent should produce PRs, not raw files.

4. **Extend task timeout** -- 10 minutes is too short for complex coding tasks. Increase to 30-60 minutes with progress heartbeats.

5. **Add test execution feedback loop** -- After generating code, run tests, parse failures, iterate. This is the core autonomous loop that separates useful agents from toys.

6. **Schedule aggressive task pickup** -- Instead of waiting for manual task submission, have the agent scan a `tasks/` directory or GitHub issues for work.

**Estimated effort**: 2-3 days of development. Zero new infrastructure.

### Medium Term (When vLLM Bug Resolved): Deploy Goose

Goose has the best headless/scheduling story of any framework evaluated. When the vLLM tool calling issue is resolved:

1. Deploy Goose via Docker on Node 1
2. Configure OpenAI provider pointing at vLLM (Qwen3.5-27B)
3. Create recipes for common tasks (code review, test generation, dependency updates, security audit)
4. Schedule recipes via cron for 24/7 operation
5. Use MCP integration for Athanor service access

**Monitor**: [GitHub Discussion #5914](https://github.com/block/goose/discussions/5914) for vLLM tool calling fix.

### Long Term: OpenHands for Complex Tasks

For SWE-bench-grade work (resolve GitHub issues, multi-file refactors):

1. Deploy OpenHands with Docker isolation
2. Route complex tasks to OpenHands, simple tasks to our agent
3. When the Python SDK stabilizes, integrate programmatically
4. Consider fine-tuning OpenHands-LM on Athanor codebase patterns

### Skip

- **Aider**: Great pair programmer, wrong architecture for 24/7 autonomous operation
- **SWE-agent**: Maintenance mode, too SWE-bench-specific
- **Devon**: Abandoned

---

## Architecture: Task Flow

```
                    Task Sources
                    ============
                    - Redis queue (manual submission)
                    - Scheduled cron jobs
                    - GitHub issue watcher (future)
                    - tasks/ directory scanner (future)
                          |
                          v
                 +------------------+
                 |  Task Router     |
                 |  (complexity     |
                 |   classifier)    |
                 +--------+---------+
                          |
              +-----------+-----------+
              |                       |
         Simple Tasks           Complex Tasks
         (< 10 min)            (> 10 min)
              |                       |
              v                       v
     +----------------+     +------------------+
     | Our coding-    |     | Goose / OpenHands|
     | agent          |     | (sandboxed)      |
     | (LangGraph)    |     |                  |
     +-------+--------+     +--------+---------+
              |                       |
              v                       v
     +------------------------------------------+
     |          /output/ staging dir             |
     |   (human review before integration)       |
     +------------------------------------------+
              |
              v
     Claude Code / Shaun reviews + integrates
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Qwen3.5-27B not available as AWQ | Low | High | Use FP8 on 5090 (32 GB), or wait for community quantization |
| Agent produces incorrect code | High | Medium | All output to staging dir, human review required |
| vLLM tool calling breaks with new model | Medium | High | Test thoroughly before production deployment |
| Agent infinite loops / runaway | Medium | Medium | Timeout enforcement, max token limits, Docker resource limits |
| Goose vLLM bug never fixed | Low | Low | Our agent + OpenHands as alternatives |

---

## Key Takeaway

**The model matters more than the framework.** Qwen3.5-27B at 72.4% SWE-bench transforms the viability of local autonomous coding. With our existing coding-agent enhanced (sandboxing, git, test feedback, longer timeouts) and Qwen3.5-27B as the backbone, we can achieve meaningful autonomous coding output at zero API cost. Goose and OpenHands are excellent frameworks to adopt once their local model stories mature, but the immediate action is: upgrade the model and enhance the agent we already have.

---

## Sources

### Agent Frameworks
- [Goose GitHub](https://github.com/block/goose) -- 30K+ stars, Apache 2.0, Block/Linux Foundation
- [Goose Provider Configuration](https://block.github.io/goose/docs/getting-started/providers/)
- [Goose Headless Mode](https://block.github.io/goose/docs/tutorials/headless-goose/)
- [Goose vLLM Tool Calling Issue](https://github.com/block/goose/discussions/5914)
- [Goose vLLM Provider Request](https://github.com/block/goose/issues/3857)
- [Aider Scripting Docs](https://aider.chat/docs/scripting.html)
- [Aider LLM Docs](https://aider.chat/docs/llms.html)
- [Aider --yes-always Bug](https://github.com/Aider-AI/aider/issues/3903)
- [OpenHands GitHub](https://github.com/OpenHands/OpenHands) -- 38K+ stars, MIT
- [OpenHands Local LLMs](https://docs.openhands.dev/openhands/usage/llms/local-llms)
- [OpenHands Headless Mode Issues](https://github.com/OpenHands/OpenHands/issues/5535)
- [OpenHands-LM-32B](https://openhands.dev/blog/introducing-openhands-lm-32b-a-strong-open-coding-agent-model)
- [SWE-agent Batch Mode](https://swe-agent.com/latest/usage/batch_mode/)
- [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) -- 100 lines, >74% SWE-bench
- [Devon GitHub](https://github.com/entropy-research/Devon)

### Models
- [Qwen3.5 Blog](https://qwen.ai/blog?id=qwen3.5) -- 27B dense, SWE-bench 72.4%
- [Qwen3.5-27B Benchmarks](https://www.digitalapplied.com/blog/qwen-3-5-medium-model-series-benchmarks-pricing-guide)
- [Qwen3.5-27B Profile](https://awesomeagents.ai/models/qwen-3-5-27b/)
- [vLLM Qwen3.5 Recipe](https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html)
- [OpenHands-LM-32B HuggingFace](https://huggingface.co/OpenHands/openhands-lm-32b-v0.1)

### Comparisons
- [Top 8 Open Source AI Coding Agents 2026](https://research.aimultiple.com/open-source-ai-coding/)
- [OpenHands vs SWE-Agent](https://localaimaster.com/blog/openhands-vs-swe-agent)
- [Best CLI Coding Agents 2026](https://pinggy.io/blog/top_cli_based_ai_coding_agents/)
- [Docker + Goose Guide](https://www.docker.com/blog/building-ai-agents-with-goose-and-docker/)
- [AMD + OpenHands Local AI](https://www.amd.com/en/developer/resources/technical-articles/2025/OpenHands.html)

Last updated: 2026-02-26
