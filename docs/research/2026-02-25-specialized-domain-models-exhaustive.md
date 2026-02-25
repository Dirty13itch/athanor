# Specialized Domain Models for Homelab Infrastructure

**Date:** 2026-02-25
**Status:** Complete -- exhaustive survey
**Scope:** SQL/database, DevOps/IaC, log analysis/AIOps, time series, smart home, security, networking, PromQL
**Window:** December 2025 -- February 2026 (with relevant earlier releases still active)

---

## Context

Athanor runs 26+ services across 4 nodes with Prometheus/Grafana monitoring, Ansible IaC, Docker Compose orchestration, Home Assistant IoT, Qdrant vector DB, Neo4j graph DB, and Redis KV. This survey identifies every specialized model that could add value beyond what the general-purpose Qwen3-32B-AWQ already provides.

**Hardware constraints for model deployment:**

| GPU | VRAM | Current Use | Available For |
|-----|------|-------------|---------------|
| 4x 5070 Ti (Node 1) | 64 GB (TP=4) | Primary vLLM | Shared -- already loaded |
| 4090 (Node 1) | 24 GB | Embedding + voice | ~8 GB free |
| 5090 (Node 2) | 32 GB | vLLM + ComfyUI | Time-shared |
| 5060 Ti (Node 2) | 16 GB | ComfyUI | Time-shared |

**Key question:** Which specialized models justify dedicated GPU allocation vs. prompting the existing Qwen3-32B-AWQ?

---

## 1. SQL / Database Query Generation

### 1.1 Dedicated Text-to-SQL Models

#### XiYan-SQL (QwenCoder Series)
- **Org:** Alibaba XGenerationLab
- **Sizes:** 3B, 7B, 14B, 32B
- **Latest:** v2504 (April 2025); QwenCoder series publicly released February 2025
- **Benchmarks:**
  - BIRD test: 75.63% EX (ensemble), 69.03% EX (32B single model, Jan 2025)
  - Spider test: 89.65% EX (Nov 2024, SOTA at time)
  - SQL-Eval: 69.86%
  - NL2GQL: 41.20% (graph query generation support)
- **License:** Apache 2.0
- **VRAM:** 7B ~6 GB (Q4), 14B ~10 GB (Q4), 32B ~20 GB (Q4)
- **HuggingFace:** `XGenerationLab/XiYanSQL-QwenCoder-32B-2502`
- **Relevance:** HIGH. Best open-source text-to-SQL model. 7B fits on any single GPU. Also supports NL2GQL which could work with Neo4j.
- **Source:** https://github.com/XGenerationLab/XiYan-SQL

#### SQLCoder (Defog)
- **Org:** Defog.ai
- **Sizes:** 7B, 7B-v2, 15B, 34B, 70B
- **Latest:** Llama-3-SQLCoder-8B (2024); SQLCoder-70B (Jan 2024)
- **Benchmarks:** SQLCoder-70B ~92% on novel schemas (n=200), outperforms GPT-4
- **License:** CC-BY-SA-4.0 (7B/15B), Apache 2.0 (Llama-3 variant)
- **VRAM:** 8B ~6 GB (Q4), 70B ~42 GB (Q4)
- **HuggingFace:** `defog/llama-3-sqlcoder-8b`, `defog/sqlcoder-70b-alpha`
- **Relevance:** MEDIUM. Strong but XiYan-SQL is newer and benchmarks higher. No updates since Jan 2024.
- **Source:** https://github.com/defog-ai/sqlcoder

#### DuckDB-NSQL-7B
- **Org:** MotherDuck / NumbersStation
- **Size:** 7B
- **Released:** January 2024
- **Benchmarks:** Trained on ~200K synthetic DuckDB queries
- **License:** Apache 2.0
- **VRAM:** ~6 GB (Q4)
- **HuggingFace:** `motherduckdb/DuckDB-NSQL-7B-v0.1`
- **Relevance:** LOW. Narrow DuckDB focus, no updates, not maintained.
- **Source:** https://github.com/NumbersStationAI/DuckDB-NSQL

#### Prem-1B-SQL
- **Org:** PremAI
- **Size:** 1B
- **Benchmarks:** Designed for laptop/edge deployment
- **License:** Unknown (check HuggingFace)
- **VRAM:** <2 GB
- **Relevance:** LOW. Too small for complex queries.

### 1.2 Recent Text-to-SQL Research (Dec 2025 -- Feb 2026)

These are frameworks/methods, not downloadable fine-tuned models, but document the state of the art:

| Paper | Date | Key Result | Open Source |
|-------|------|------------|-------------|
| **MATS** (Multi-Agent Text2SQL) | Dec 2025 | Single-GPU server, accuracy on-par with large LLMs | GitHub |
| **EvolSQL** | Jan 2026 | 7B model outperforms larger datasets using 1/18 data | GitHub |
| **RingSQL** | Jan 2026 | +2.3% accuracy across six benchmarks via synthetic data | GitHub |
| **RoboPhD** | Jan 2026 | Self-improving text-to-SQL, evolved Sonnet > naive Opus | -- |
| **IESR** | Feb 2026 | MCTS-based reasoning, SOTA on LogicCat with lightweight models | GitHub |
| **SWE-SQL** | Jun 2025 (updated Jan 2026) | Qwen-2.5-Coder-14B: 38.11% on BIRD-CRITIC-PG | -- |
| **LLMSQL** | Sep 2025 (updated Dec 2025) | Models <10B surpass 90% accuracy after fine-tuning on cleaned WikiSQL | -- |
| **LearNAT** | Apr 2025 | 7B open-source matches GPT-4 via AST-guided decomposition | -- |

**Source:** https://arxiv.org search, https://github.com/eosphoros-ai/Awesome-Text2SQL

### 1.3 Benchmark Leaderboards (Current)

**BIRD Test Set (Feb 2026):**

| Rank | Model/System | EX (%) | Org | Date |
|------|-------------|--------|-----|------|
| 1 | AskData + GPT-4o | 81.95 | AT&T CDO | Sep 2025 |
| 2 | Agentar-Scale-SQL | 81.67 | Ant Group | Jul 2025 |
| 3 | Zhiwen-Lingsi-Agent | 76.63 | China Telecom | Jan 2026 |
| 4 | DeepEye-SQL | 76.58 | Anonymous | Dec 2025 |
| 5 | Q-SQL | 76.47 | AWS | Feb 2026 |

**Spider 2.0-Snow (Feb 2026):**

| Rank | Method | Score (%) | Org |
|------|--------|-----------|-----|
| 1 | QUVI-3 + Gemini-3-pro | 94.15 | DAQUV |
| 2 | TCDataAgent-SQL | 93.97 | Tencent Cloud |
| 3 | Native mini | 92.50 | usenative.ai |
| 4 | Prism Swarm + Claude-Sonnet-4.5 | 90.49 | Paytm |

**Source:** https://bird-bench.github.io/, https://spider2-sql.github.io/

---

## 2. Graph Query Generation (Cypher, SPARQL, GraphQL)

### 2.1 Cypher (Neo4j)

**No dedicated open-source Cypher model exists.** The state of the art is prompting general LLMs with schema context. Key research:

| Paper | Date | Key Finding | Models Tested |
|-------|------|-------------|---------------|
| **Auto-Cypher** | Dec 2024 / NAACL 2025 | Synthetic data yields +40% on Text2Cypher | LLaMA-3.1-8B, Mistral-7B, Qwen-7B |
| **Text2Cypher Schema Filtering** | May 2025 | Schema filtering optimizes smaller models, reduces tokens | Multiple sizes |
| **GraphRAFT** | Apr 2025 | Fine-tuned LLMs generate provably correct Cypher, SOTA on 2 benchmarks | Not specified |

**Neo4j ecosystem tooling:**
- `neo4j-graphrag-python` with `Text2CypherRetriever` -- uses any LLM via LangChain/Ollama/OpenAI APIs
- No Neo4j-specific fine-tuned model weights released

**Recommendation:** Use Qwen3-32B with Neo4j schema injection via Text2CypherRetriever. Fine-tuning a 7-8B model on your specific graph schema would yield better results than any general model.

**Source:** https://neo4j.com/labs/genai-ecosystem/, arXiv search

### 2.2 SPARQL

| Paper | Date | Key Result | Model |
|-------|------|------------|-------|
| **SPARQL-LLM** | Dec 2025 | +24% F1, 36x faster, <$0.01/question | Lightweight LLM (unspecified) |
| **3B RL Agent** | Nov 2025 | +17.5% over strongest zero-shot baseline | 3B parameters, RL-trained |
| **Chatty-KG** | Nov 2025 | Multi-agent SPARQL via dialogue | GPT-4o, Gemini-2.0, Phi-4, Gemma 3 |
| **GRASP** | Jul 2025 | SOTA on Wikidata, zero-shot | Not specified |

**Relevance:** LOW for Athanor. No SPARQL endpoints in the current stack.

### 2.3 GraphQL

| Paper | Date | Key Result |
|-------|------|------------|
| **PrediQL** | Oct 2025 | LLM + RAG for GraphQL fuzzing/testing, not generation |

**Relevance:** MEDIUM. Stash uses GraphQL. No dedicated model exists; prompt Qwen3-32B with schema.

---

## 3. DevOps / Infrastructure-as-Code

### 3.1 Dedicated DevOps Models

**No production-quality dedicated DevOps model exists as a downloadable fine-tuned checkpoint.** The landscape is dominated by:
1. General coding models (Qwen2.5-Coder, DeepSeek-Coder) prompted with IaC context
2. Agent frameworks that orchestrate LLMs for IaC tasks
3. Ollama community models (all system-prompt wrappers, not fine-tuned)

**Ollama "DevOps" models (all system-prompt wrappers):**

| Model | Base | Downloads | Updated |
|-------|------|-----------|---------|
| `omidzamani/devops-elite` | Unknown | 54 | Dec 2025 |
| `jimscard/devopd` | dolphin-mistral 7B | 779 | 2024 |
| `themanofrod/devsecops-engineer` | Unknown | 112 | 2024 |

**None of these are fine-tuned.** They are system-prompt wrappers around general models.

### 3.2 IaC Research (Dec 2025 -- Feb 2026)

| Paper | Date | Focus | Key Result | Open Source |
|-------|------|-------|------------|-------------|
| **TerraFormer** | Jan 2026 (ICSE 2026) | Terraform generation | +15.94% correctness on IaC-Eval via RL | CC-BY-NC-ND 4.0 |
| **IaC Security (Can Developers Rely...)** | Feb 2026 | Terraform security | Only 7-17% of LLM-generated scripts secure | -- |
| **IntelliSA** | Jan 2026 (MSR 2026) | IaC security scanning | 83% F1, 500x smaller student model | Unknown |
| **GenSIaC** | Nov 2025 | Security-aware IaC | F1 0.303 -> 0.858 with instruction fine-tuning | -- |
| **KubeIntellect** | Sep 2025 | Kubernetes configs | 93% tool synthesis, 100% reliability on 200 NL queries | -- |
| **MACOG** | Oct 2025 | Multi-agent IaC | GPT-5: 54.90% -> 74.02% on IaC-Eval | -- |
| **Multi-IaC-Eval** | Sep 2025 | Benchmark | >95% syntactic validity, weak semantic alignment | Multi-IaC-Bench released |
| **IaCGen** | Jun 2025 (FSE 2026) | Deployable templates | 54.6-91.6% deployable in 10 iterations | -- |

**Recommendation:** No specialized model to download. Continue using Qwen3-32B-AWQ with Ansible/Docker context injection. The research shows that IaC generation benefits more from agentic loops with validation feedback than from specialized models.

**Source:** arXiv search for IaC, Terraform, Kubernetes LLM

### 3.3 Shell/Bash Generation

No dedicated bash/shell models found in the search window. General coding models (Qwen2.5-Coder, DeepSeek-Coder) handle this well. No specialized fine-tune needed.

---

## 4. Log Analysis / AIOps

### 4.1 Log Parsing Models

| Paper/Tool | Date | Model | Key Result | Open Source |
|------------|------|-------|------------|-------------|
| **MicLog** | Jan 2026 | Qwen-2.5-3B | +10.3% parsing accuracy, -42.4% time vs SOTA | -- |
| **EFParser** | Jan 2026 | Small LLM (unspecified) | +12.5% across metrics on smaller LLMs, dual-cache | -- |
| **EnrichLog** | Dec 2025 | RAG-based (training-free) | Improved anomaly detection across 4 benchmarks | -- |
| **LogICL** | Dec 2025 | Distilled lightweight encoder | Cross-domain detection with few-shot | -- |

**Key finding:** MicLog demonstrates that Qwen-2.5-3B (which we could run on any GPU with <3 GB VRAM) achieves SOTA log parsing with meta in-context learning. This is directly applicable to parsing Prometheus/Docker/Nginx logs.

### 4.2 Root Cause Analysis

| Paper | Date | Key Result | Open Source |
|-------|------|------------|-------------|
| **RC-LLM** | Feb 2026 | Multi-source RCA (metrics+logs+traces) for microservices | -- |
| **MicroRCA-Agent** | Sep 2025 | Drain log parsing + Isolation Forest, score 50.71 | GitHub (tangpan360/MicroRCA-Agent) |
| **GALA** | Aug 2025 | Causal inference + LLM reasoning, +42.22% accuracy | -- |
| **Flow-of-Action** | Feb 2025 (WWW'25) | SOP-enhanced multi-agent, 64.01% vs ReAct 35.50% | -- |
| **KnowledgeMind** | Jul 2025 | MCTS + reward mechanism, +49-128% improvement | -- |

**Source:** arXiv search for root cause analysis microservice LLM

### 4.3 Anomaly Detection

| Paper | Date | Key Result | Open Source |
|-------|------|------------|-------------|
| **CAPMix** | Sep 2025 | Robust time series anomaly detection, dual-space mixup | GitHub (alsike22/CAPMix) |

### 4.4 PromQL Generation

**PromAssistant** (March 2025)
- **First text-to-PromQL framework**
- Combines LLM + knowledge graph for Prometheus metric queries
- 280-question benchmark dataset (first of its kind)
- Outperforms baselines
- **No model weights released** -- framework-level contribution
- arXiv: 2503.03114

**Relevance:** HIGH conceptual value. No downloadable model, but the approach (LLM + metric knowledge graph) could be replicated with Qwen3-32B + a Prometheus metric schema injected as context.

**Source:** https://arxiv.org/abs/2503.03114

### 4.5 Observability Tooling

| Tool | Date | Focus | Open Source |
|------|------|-------|-------------|
| **AgentTrace** | Feb 2026 | Structured logging for LLM agents | Framework |
| **AgentSight** | Aug 2025 | eBPF-based observability for AI agents, <3% overhead | GitHub (agent-sight/agentsight) |

**Source:** arXiv search for LLM observability monitoring

---

## 5. Time Series Foundation Models

### 5.1 Models Relevant to Infrastructure Monitoring

#### IBM Granite TinyTimeMixer (TTM) r2/r2.1
- **Parameters:** 805K -- 1M (extremely lightweight)
- **Tasks:** Forecasting (zero-shot and fine-tuned), multivariate, exogenous variables
- **Benchmarks:** Outperforms TimesFM, Chronos, Moirai, MOMENT; TTM r2 > r1 by 15%
- **VRAM:** Runs on CPU. No GPU needed.
- **License:** Apache 2.0
- **Latest release:** v0.3.3 (January 21, 2026)
- **HuggingFace:** `ibm-granite/granite-timeseries-ttm-r2`
- **Relevance:** VERY HIGH. 805K params means zero GPU cost. Could run anomaly detection on Prometheus metrics on CPU. Apache 2.0.
- **Source:** https://github.com/IBM/tsfm, https://huggingface.co/ibm-granite/granite-timeseries-ttm-r2

#### Google TimesFM 2.5
- **Parameters:** 200M (down from 500M in v2.0)
- **Context Length:** Up to 16K tokens
- **Tasks:** Point forecasting, continuous quantile forecasting (10th-90th percentile)
- **VRAM:** ~1-2 GB
- **License:** Apache 2.0
- **Released:** September 2025
- **HuggingFace:** `google/timesfm-2.5-200m`
- **Relevance:** HIGH. Small enough for CPU or minimal GPU. Good for Prometheus metric forecasting.
- **Source:** https://github.com/google-research/timesfm

#### Amazon Chronos-2
- **Parameters:** 120M (main), 28M (small)
- **Tasks:** Univariate, multivariate, covariate-informed forecasting
- **Benchmarks:** >90% win rate vs Chronos-Bolt
- **VRAM:** Minimal (Bolt variants "250x faster, 20x more memory efficient")
- **License:** Apache 2.0
- **Released:** October 2025
- **HuggingFace:** `amazon/chronos-2`, `autogluon/chronos-2-small`
- **Relevance:** HIGH. 28M small variant could run on CPU for metric forecasting.
- **Source:** https://github.com/amazon-science/chronos-forecasting

#### MOMENT
- **Sizes:** Small, Base, Large
- **Tasks:** Forecasting, classification, anomaly detection, imputation
- **Benchmarks:** Second-best F1 for anomaly detection, outperforms 11/16 methods in classification
- **VRAM:** "Single A6000 48 GB" for full training; inference much less
- **License:** MIT
- **Released:** May 2024 (ICML 2024), actively maintained
- **HuggingFace:** `AutonLab/MOMENT-1-large`, `AutonLab/MOMENT-1-base`, `AutonLab/MOMENT-1-small`
- **Relevance:** MEDIUM-HIGH. Supports anomaly detection natively. MIT license.
- **Source:** https://github.com/moment-timeseries-foundation-model/moment

#### Cisco Time Series Model
- **Architecture:** Multiresolution decoder-only (TimesFM variant)
- **Training:** 300B+ unique data points
- **Focus:** Observability datasets specifically
- **Released:** November 2025
- **VRAM:** Unknown
- **License:** Unknown (may be proprietary)
- **Relevance:** HIGH if available. Purpose-built for monitoring/observability data.

#### Tiny-TSM
- **Parameters:** 23M
- **Training:** Single A100, <1 week
- **Benchmarks:** Outperforms larger models on medium/long-term forecasting
- **Released:** November 2025
- **Relevance:** MEDIUM. Another lightweight option.

#### FLAME
- **Architecture:** Legendre Memory-based
- **Benchmarks:** SOTA zero-shot on deterministic and probabilistic tasks
- **Released:** December 2025
- **Relevance:** MEDIUM. Lightweight foundation model.

---

## 6. Smart Home / IoT

### 6.1 Home-LLM
- **Org:** acon96
- **Latest:** v0.4.6 (January 2026)
- **Models:** Llama 3.2 3B, Gemma 270M
- **Capabilities:** Lights, switches, fans, covers, locks, climate, media, vacuums, buttons, timers, todo lists, scripts. Voice/chat control, tool calling with agentic loops.
- **Requirements:** Runs on Raspberry Pi. No GPU needed.
- **Backends:** Llama.cpp, Ollama, OpenAI-compatible APIs, Anthropic APIs
- **License:** Open source (specific terms in LICENSES.txt)
- **Relevance:** HIGH. Direct HA integration. v0.4.6 adds Anthropic API support and new tool-calling dataset. Could supplement the existing HA voice pipeline.
- **Source:** https://github.com/acon96/home-llm

### 6.2 Research Models

| Paper | Date | Key Finding | Relevance |
|-------|------|-------------|-----------|
| **DomusFM** | Feb 2026 | First foundation model for smart-home sensor data, outperforms with 5% labeled data | MEDIUM (sensor activity recognition) |
| **ECO-LLM** | Jul 2025 | Edge-cloud orchestrator, 90% accuracy vs GPT-4o 74%, 90% cost reduction | HIGH (edge inference architecture) |
| **HomeLLaMA** | Jul 2025 | Privacy-preserving on-device HA assistant with PrivShield | MEDIUM (privacy focus) |
| **On-Device LLMs for HA** | Feb 2025 | 80-86% accuracy on noisy prompts, CPU-only, 5-6s inference | HIGH (proves small models work for HA) |
| **HA Automation Generation** | May 2025 | GPT generates valid HA automations, 56-user study | LOW (uses GPT, not local) |
| **Smart Home Voice Rejection** | Dec 2025 | Qwen-2.5-3B adapter, 3-tier arch, outperforms general LLMs | HIGH (query filtering for voice) |

**Source:** arXiv search for Home Assistant, smart home language model

---

## 7. Code Security / Vulnerability Detection

### 7.1 Deployable Models

| Model/Paper | Date | Size | Key Result | Open Source |
|-------------|------|------|------------|-------------|
| **DAGVul** | Feb 2026 | 8B | +18.9% F1, competitive with Claude-Sonnet-4.5 | Likely |
| **PSSec** | Jan 2026 | 1.7B+ | Matches large models on PowerShell security | GPT/Qwen families |
| **Llama-3.1-8B vuln detection** | Dec 2025 | 8B | Double fine-tuning approach | GitHub |
| **CGP-Tuning** | Jan 2025 | Various | CodeLlama, CodeGemma, Qwen2.5-Coder with graph enhancement | -- |

### 7.2 Frameworks (Not Downloadable Models)

| Framework | Date | Key Result |
|-----------|------|------------|
| **SecCodePRM** | Feb 2026 | Process reward model for code security, outperforms prior approaches |
| **QRS** | Feb 2026 | 90.6% detection on 20 CVEs, found 5 new CVEs in PyPI |
| **SecCoderX** | Feb 2026 | +10% Effective Safety Rate via online RL |
| **AgenticSCR** | Jan 2026 | +153% correct review comments vs static baseline |
| **Co-RedTeam** | Feb 2026 | 60%+ vulnerability exploitation success |

**Relevance:** MEDIUM. An 8B vulnerability scanner (DAGVul) could run on the 4090 alongside embedding, but the practical value for a homelab is limited vs. just using the general Qwen3-32B for code review.

**Source:** arXiv search for code vulnerability detection LLM

---

## 8. Network Configuration

| Paper | Date | Key Result | Model |
|-------|------|------------|-------|
| **SLM_netconfig** | Dec 2025 | Fine-tuned SLM > LLM-NetCFG accuracy, lower latency | Small LM (unspecified) |
| **NetMind** | Oct 2025 | Tree-based config chunking, vendor-agnostic | LLM framework |
| **NL Firewall Config** | Dec 2025 | 3-layer validation (linter + safety gate + Batfish simulator) | LLM as parser |
| **5G with LLaMA-3 8B** | Nov 2025 | Local RAG-enhanced config generation | LLaMA-3 8B Q4 |

**Relevance:** LOW. UniFi configs are managed through the UDM Pro UI, not raw CLI. These are more relevant to enterprise network engineering.

**Source:** arXiv search for network configuration language model

---

## 9. API / Documentation Generation

| Paper | Date | Key Result |
|-------|------|------------|
| **OASBuilder** | Jul 2025 | HTML docs -> OpenAPI specs, saves thousands of hours |
| **ACE Framework** | Sep 2025 | -25% payload formation errors for API tools |
| **GOAT** | Oct 2025 | Synthetic API execution datasets from docs |

**Relevance:** LOW. General coding models handle API docs well.

---

## 10. Regex / YAML / Configuration Generation

No dedicated models found. Research papers focus on:
- Regex vulnerability repair (Oct 2025, symbolic + LLM hybrid)
- YAML generation for Kubernetes (KubeIntellect, Sep 2025)
- LLM-FSM for FSM YAML specs (Feb 2026)

**Recommendation:** General coding models handle regex and YAML generation adequately.

---

## Synthesis: What Matters for Athanor

### Tier 1: Deploy Now (High Value, Low Cost)

| Model | Task | Size | GPU Needed | Why |
|-------|------|------|-----------|-----|
| **IBM TTM r2.1** | Prometheus metric forecasting + anomaly detection | 805K | CPU only | Predict disk full, detect metric anomalies, zero GPU cost |
| **Home-LLM v0.4.6** | HA device control | 270M-3B | CPU or shared | Direct HA integration, supplements voice pipeline |
| **Chronos-2 Small** | Time series forecasting | 28M | CPU only | Backup/alternative to TTM for metric prediction |

### Tier 2: Worth Evaluating (High Value, Some Cost)

| Model | Task | Size | GPU Needed | Why |
|-------|------|------|-----------|-----|
| **XiYan-SQL 7B** | Text-to-SQL for Qdrant/metrics analysis | 7B | ~6 GB (Q4) | Best open-source text-to-SQL, could query exported Prometheus data |
| **TimesFM 2.5** | Metric forecasting with quantile estimation | 200M | ~1-2 GB | Probabilistic forecasts (confidence intervals) for alerts |
| **MOMENT** | Anomaly detection + classification | Various | Small | MIT license, native anomaly detection support |
| **Qwen-2.5-3B** (MicLog approach) | Log parsing | 3B | ~3 GB | SOTA log parsing via meta in-context learning |

### Tier 3: Not Worth Dedicated Deployment

| Category | Reason |
|----------|--------|
| **DevOps/IaC models** | No fine-tuned models exist. Qwen3-32B with context injection is the right approach. |
| **Cypher models** | No dedicated model. Use Qwen3-32B + Neo4j schema via Text2CypherRetriever. |
| **Security models** | 8B vuln scanners exist but marginal value for homelab vs. general model. |
| **Network models** | UniFi managed via UI, not raw configs. |
| **API/docs models** | General coding models handle this. |
| **PromQL models** | No downloadable model. PromAssistant is a framework. Prompt Qwen3-32B with metric schema. |
| **SPARQL models** | No SPARQL endpoints in stack. |
| **Regex/YAML models** | No dedicated models exist. General models handle this. |

---

## Key Findings

1. **The specialized model landscape is thin.** Outside of text-to-SQL and time series, there are very few downloadable fine-tuned models. Most "specialized" work is frameworks/agents that prompt general LLMs with domain context.

2. **Time series foundation models are the biggest win.** IBM TTM at 805K params on CPU can do metric forecasting and anomaly detection. This is free compute that adds real monitoring intelligence.

3. **Text-to-SQL models are mature.** XiYan-SQL 7B is genuinely better than prompting a general 32B model for SQL generation. Worth deploying if we add SQL-queryable data sources.

4. **Home-LLM is production-ready.** v0.4.6 (Jan 2026) with Ollama backend could enhance the HA voice pipeline with device control intelligence.

5. **Log parsing benefits from small specialized models.** MicLog shows Qwen-2.5-3B with meta-ICL beats larger general models at log parsing. This could run on the 4090 spare capacity.

6. **DevOps/IaC is a dead end for specialized models.** The research unanimously shows that agentic loops with validation feedback matter more than model specialization. Continue using Qwen3-32B with Ansible/Docker context.

7. **No PromQL model exists as a downloadable artifact.** PromAssistant is the closest, but it is a framework paper. The approach (inject metric schema as context) is what we should replicate with Qwen3-32B.

---

## Open Questions

1. Is IBM TTM r2.1 available on HuggingFace with a simple inference API, or does it require the full `granite-tsfm` toolkit?
2. Can Home-LLM v0.4.6 route through LiteLLM proxy (OpenAI-compatible), or does it need direct Ollama?
3. What is the actual VRAM footprint of XiYan-SQL 7B with AWQ quantization on vLLM?
4. Could MicroRCA-Agent (open-source RCA tool) integrate with our Prometheus/Loki stack?

---

## Sources

- BIRD Benchmark: https://bird-bench.github.io/
- Spider 2.0: https://spider2-sql.github.io/
- XiYan-SQL: https://github.com/XGenerationLab/XiYan-SQL
- SQLCoder: https://github.com/defog-ai/sqlcoder
- DuckDB-NSQL: https://github.com/NumbersStationAI/DuckDB-NSQL
- Awesome-Text2SQL: https://github.com/eosphoros-ai/Awesome-Text2SQL
- Neo4j GenAI: https://neo4j.com/labs/genai-ecosystem/
- Neo4j GraphRAG: https://github.com/neo4j/neo4j-graphrag-python
- Home-LLM: https://github.com/acon96/home-llm
- IBM TTM: https://github.com/IBM/tsfm, https://huggingface.co/ibm-granite/granite-timeseries-ttm-r2
- TimesFM: https://github.com/google-research/timesfm
- Chronos: https://github.com/amazon-science/chronos-forecasting
- MOMENT: https://github.com/moment-timeseries-foundation-model/moment
- PromAssistant: https://arxiv.org/abs/2503.03114
- MicroRCA-Agent: https://github.com/tangpan360/MicroRCA-Agent
- AgentSight: https://github.com/agent-sight/agentsight
- CAPMix: https://github.com/alsike22/CAPMix
- Ollama SQL models: https://ollama.com/search?q=sql
- Ollama DevOps models: https://ollama.com/search?q=devops
- arXiv searches: text-to-SQL, DevOps LLM, log analysis LLM, IaC generation, time series foundation model, vulnerability detection, network config LLM, Cypher generation, SPARQL generation, PromQL generation, regex generation, API documentation generation, smart home LLM, YAML generation
- Defog blog: https://defog.ai/blog/
