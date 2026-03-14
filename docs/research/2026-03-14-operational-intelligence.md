# Operational Intelligence Enhancements — March 2026

*Research via local Research Agent, 2026-03-14. Thorough depth.*

## AdaptOrch: Topology-Aware Routing

- **Paper**: arxiv.org/html/2602.16873v1 — formal framework for task-adaptive multi-agent orchestration
- Dynamically selects among 4 canonical topologies: parallel, sequential, hierarchical, hybrid
- Performance Convergence Scaling Law: under ε-convergence of model capabilities, orchestration topology variance exceeds model selection variance by Ω(1/ε²)
- Topology routing algorithm: analyzes task dependency DAGs in O(|V|+|E|) time
- **For Athanor**: Could improve our 9-agent LangGraph system by 12-23% via dynamic topology selection
- **Action**: Research-grade paper, no production implementation available yet. Monitor for open-source releases.

## Audio Intelligence Layer

### Snipd → Readwise → NotebookLM Pipeline
- Snipd auto-syncs podcast highlights to Readwise
- Readwise exports to NotebookLM via Google Docs integration
- Creates seamless: highlight → sync → analyze workflow

### Local-NotebookLM
- **v2.0.0** (Feb 2026) on PyPI
- Local AI-powered PDF-to-audio conversion using local LLMs + TTS
- Could run on VAULT or DEV for research paper processing
- Uses local models — no cloud dependency

### Recommendation
- Low priority for Athanor currently — Shaun doesn't have heavy podcast/audio research workflow
- Worth revisiting if audio processing becomes a priority

## Agentic RSS Classification

### n8n + Miniflux + Small LLM
- `n8n-nodes-miniflux` community node enables Miniflux integration with n8n
- Production pattern: Miniflux → n8n trigger → LLM classify/summarize → store/alert
- Qwen3.5-9B sufficient for feed classification (10.6GB VRAM)

### Current State in Athanor
- Miniflux deployed (VAULT:8070, 17 feeds, 6 categories)
- n8n deployed (VAULT:5678, 5 workflows)
- Intelligence Signal Pipeline exists but needs activation by Shaun
- **Gap**: No LLM classification in the pipeline — just fetch/embed/store

### Recommended Enhancement
- Add LLM classification node to Signal Pipeline using `fast` model (Qwen3-8B)
- Categories: actionable, informational, monitor, ignore
- Route actionable signals to ntfy for immediate notification

## Benchmark Suites

### GuideLLM (vllm-project)
- SLO-aware benchmarking for real-world LLM inference
- Complete latency and token-level statistics
- Supports multimodal (text, image, audio, video)
- Output: JSON, CSV, HTML reports
- **Best for**: Production throughput measurement

### lm-evaluation-harness (EleutherAI)
- v0.4.0 (Dec 2025) with vLLM backend support
- 60+ standard academic benchmarks
- **Best for**: Model quality comparison

### For Athanor
- Already have basic promptfoo eval (16 prompts × 3 models)
- GuideLLM would add throughput regression testing
- lm-eval would add standardized quality baselines
- **Action**: Install GuideLLM, run baseline on coordinator + worker models

## Sources
- https://arxiv.org/html/2602.16873v1
- https://github.com/vllm-project/guidellm
- https://github.com/EleutherAI/lm-evaluation-harness
- https://support.snipd.com/en/articles/10226077-sync-your-snips-to-readwise
- https://pypi.org/project/local-notebooklm/
- https://github.com/that-one-tom/n8n-nodes-miniflux

Last updated: 2026-03-14
