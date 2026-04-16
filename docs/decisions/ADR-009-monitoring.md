# ADR-009: Monitoring + Observability

**Date:** 2026-02-15
**Status:** Accepted
**Research:** [docs/archive/research/2026-02-15-monitoring.md](../archive/research/2026-02-15-monitoring.md)
**Depends on:** ADR-004 (Node Roles)

---

## Context

Athanor has 4 machines, 7 GPUs, and dozens of Docker containers running inference, creative pipelines, media services, and home automation. Without monitoring, failures are discovered when something stops working. With monitoring, failures are caught before they cascade, GPU utilization is visible, and system health is glanceable from the dashboard.

This is not a research-heavy decision. Prometheus + Grafana is the standard monitoring stack for Docker-based systems. The question is configuration, not tool selection.

---

## Decision

### Prometheus + Grafana on VAULT with exporters on all nodes.

#### Central Monitoring (VAULT — always-on)

| Service | Port | Docker | Purpose |
|---------|------|--------|---------|
| Prometheus | 9090 | Yes | Metrics collection and storage |
| Grafana | 3000 | Yes | Dashboards and visualization |
| Alertmanager | 9093 | Yes | Alert routing (email, Discord, webhook) |

VAULT runs monitoring because it's always on (ADR-004). If a compute node goes down, monitoring still works and can alert.

#### Exporters (Node 1 + Node 2)

| Exporter | Port | Purpose |
|----------|------|---------|
| node_exporter | 9100 | CPU, RAM, disk, network |
| dcgm-exporter | 9400 | GPU utilization, VRAM, temp, power, clocks |
| cAdvisor | 8080 | Per-container CPU, memory, network |

#### Exporter (VAULT)

| Exporter | Port | Purpose |
|----------|------|---------|
| Unraid Prometheus plugin | 9100 | System metrics (installed via CA) |

#### Application Metrics (No extra exporters needed)

| Service | Metrics Source | Key Metrics |
|---------|---------------|-------------|
| vLLM (Node 1, Node 2) | Built-in /metrics endpoint | Throughput (tok/s), latency (TTFT), queue depth, KV cache usage |
| ComfyUI (Node 2) | API status endpoint | Active jobs, queue length |

---

## Key Dashboards

Pre-built Grafana dashboards where available, custom panels where needed:

| Dashboard | Source | What It Shows |
|-----------|--------|---------------|
| NVIDIA DCGM | [Grafana #12239](https://grafana.com/grafana/dashboards/12239) | Per-GPU utilization, VRAM, temp, power |
| Node Exporter Full | [Grafana #1860](https://grafana.com/grafana/dashboards/1860) | Per-node CPU, RAM, disk, network |
| Docker/cAdvisor | [Grafana #893](https://grafana.com/grafana/dashboards/893) | Per-container resource usage |
| vLLM Inference | Custom | Throughput, latency, queue depth, models loaded |
| Athanor Overview | Custom | Summary panel for dashboard integration (ADR-007) |

---

## Alert Rules

Start with essentials, add more as patterns emerge:

| Alert | Condition | Severity |
|-------|-----------|----------|
| GPU Overtemp | GPU temp > 85°C for 5 min | Critical |
| Disk Full | Disk usage > 90% | Warning |
| Disk Critical | Disk usage > 95% | Critical |
| Service Down | Docker container exited | Warning |
| vLLM Down | vLLM not responding for 2 min | Critical |
| High GPU Memory | VRAM > 95% for 10 min | Warning |
| VAULT Array Error | Unraid disk error | Critical |

Alert routing via Alertmanager to Discord webhook (or email). The dashboard (ADR-007) also shows active alerts.

---

## Dashboard Integration (ADR-007)

Athanor's custom dashboard queries Prometheus's HTTP API for summary metrics:

```
GET http://vault:9090/api/v1/query?query=DCGM_FI_DEV_GPU_UTIL
GET http://vault:9090/api/v1/query?query=node_memory_MemAvailable_bytes
GET http://vault:9090/api/v1/query?query=vllm:num_requests_running
```

The dashboard shows at-a-glance health. Grafana is one click away for deep dives.

---

## Data Retention

| Metric Type | Retention | Reasoning |
|-------------|-----------|-----------|
| Raw metrics (15s interval) | 15 days | Detailed troubleshooting |
| Downsampled (5m averages) | 90 days | Trend analysis |
| Aggregated (1h averages) | 1 year | Capacity planning |

Prometheus local storage with recording rules for downsampling. At 15s scrape intervals across ~20 targets with ~200 metrics each, storage is ~2-5 GB per month. VAULT's NVMe handles this easily.

---

## What This Enables

- **Glanceable health** — GPU temps, VRAM usage, inference throughput visible from the dashboard
- **Proactive alerting** — know about problems before they cause failures
- **Performance tuning** — see actual throughput/latency for vLLM, identify bottlenecks
- **Capacity planning** — trend data shows when storage, VRAM, or compute is trending toward limits
- **Debugging** — correlate GPU spikes with container activity and inference requests

---

## Alternatives Considered

| Alternative | Why Not |
|-------------|---------|
| InfluxDB + Telegraf | Valid, but Prometheus has better GPU/Docker exporter ecosystem. No advantage to switching. |
| Cloud monitoring (Datadog, New Relic) | Costs money, sends data off-network. Prometheus is free and local. |
| Zabbix | Enterprise-oriented, heavier than needed for 4 machines. |
| nvidia-smi only | No history, no dashboards, no alerting. Fine for spot checks. |
| No monitoring | Unacceptable. Athanor is too complex to fly blind. |

---

## Risks

- **DCGM on consumer GPUs.** DCGM is designed for datacenter GPUs. It works on consumer GPUs but some metrics may be unavailable (e.g., NVLink counters). Fallback: nvidia-smi exporter provides basic GPU metrics if DCGM has issues.
- **Prometheus storage growth.** At high scrape frequencies with many targets, storage can grow. Mitigated by recording rules for downsampling and configurable retention.
- **Alert fatigue.** Too many alerts desensitize. Start with critical-only alerts, add warnings only when they're actionable.

---

## Sources

- [DCGM-Exporter GitHub](https://github.com/NVIDIA/dcgm-exporter)
- [DCGM-Exporter Grafana dashboard](https://grafana.com/grafana/dashboards/12239-nvidia-dcgm-exporter-dashboard/)
- [vLLM + DCGM monitoring](https://medium.com/@kimdoil1211/how-to-monitor-gpu-cpu-and-memory-usage-of-a-vllm-server-using-prometheus-dcgm-exporter-f988afd70460)
- [Unraid Prometheus monitoring](https://unraid.net/blog/prometheus)
- [Unraid node_exporter plugin](https://github.com/ich777/unraid-prometheus_node_exporter)
- [Unraid monitoring forum thread](https://forums.unraid.net/topic/77593-monitoring-unraid-with-prometheus-grafana-cadvisor-nodeexporter-and-alertmanager/)
