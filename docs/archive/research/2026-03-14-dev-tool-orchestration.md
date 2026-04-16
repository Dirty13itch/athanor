# Developer Tool Orchestration — March 2026

*Research via local Research Agent, 2026-03-14. Thorough depth.*

## Claude Code with Local Models

- **ANTHROPIC_BASE_URL** can point to LiteLLM proxy → route to local vLLM
- Ollama v0.14.0+ provides native Anthropic-compatible API
- LiteLLM requires `anthropic_beta_headers_config.json` to handle Claude Code beta headers
- llama.cpp server on :8001 with temp 0.6, top_p 0.95, top_k 20, KV cache q8_0 for VRAM efficiency
- **Practical**: Can reduce API costs 70-80% by routing routine coding to local Qwen3.5

## Claude Code Agent Teams (Swarms)

- **Officially launched** February 2026 alongside Opus 4.6
- Enable: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
- Architecture: team lead coordination, independent context windows per teammate, shared task lists, peer-to-peer messaging
- Supports split-pane mode (tmux/iTerm2)
- Multi-agent patterns: Leader (hierarchical), Swarm (parallel), Pipeline (sequential), Council (multi-perspective), Watchdog (quality monitoring)

## Tool Comparison

| Feature | Claude Code | Aider | OpenCode | Goose |
|---------|------------|-------|----------|-------|
| Stars | N/A (closed) | 41K | 121K | ~10K |
| License | Proprietary | Apache 2.0 | MIT | Apache 2.0 |
| Models | Anthropic (local via proxy) | 75+ providers | 75+ providers | LiteLLM + MCP |
| Key Strength | Complex architecture | Git-native workflows | LSP integration (~40 langs) | Infrastructure recipes |
| Maturity | 2+ years | 3+ years | ~11 months | ~1 year |
| SWE-bench | 80.9% (Opus 4.5) | Varies by model | Varies by model | N/A |

## Goose Recipe Ecosystem

- Reusable YAML/JSON workflow files with prompts, parameters, MCP servers, settings
- Supports subrecipes for parallel execution
- Athanor already has 2 recipes: `port-hydra-module.yaml`, `test-all-endpoints.yaml`
- Opportunity: Create maintenance recipes (backup verification, model health, node audit)

## Recommendations for Athanor

1. **Try Agent Teams** — enable `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` for complex multi-file work
2. **Evaluate OpenCode** — 121K stars, MIT license, LSP integration for TypeScript projects (dashboard/EoBQ)
3. **Expand Goose recipes** — infrastructure automation (nightly ops, backup verify, model deploy)
4. **Keep current stack** — Claude Code (complex) + Aider (routine) + Goose (recipes) is the right split

## Sources
- https://code.claude.com/docs/en/agent-teams
- https://docs.litellm.ai/docs/tutorials/claude_code_beta_headers
- https://block.github.io/goose/docs/guides/recipes/
- https://www.morphllm.com/ai-coding-agent
- https://openalternative.co/compare/aider/vs/opencode
- https://docs.ollama.com/integrations/claude-code

Last updated: 2026-03-14
