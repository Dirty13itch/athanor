# Monitoring + Observability

> Historical note: archived research retained for ADR-009 decision history. Current health, service, and observability truth lives in the topology registry, service contracts, and generated reports.

**Date:** 2026-02-15
**Status:** Complete — recommendation ready
**Supports:** ADR-009 (Monitoring + Observability)
**Depends on:** ADR-004 (Node Roles)

---

## The Question

How does Athanor monitor system health, GPU utilization, inference performance, and service status across all four machines?

---

## Requirements

1. **GPU monitoring** — VRAM usage, utilization, temperature, power draw for all 7 GPUs across 3 nodes
2. **System metrics** — CPU, RAM, disk, network for all machines
3. **Service health** — Docker container status, vLLM instance health, inference throughput/latency
4. **Alerting** — notify when things break (GPU overtemp, disk full, service down)
5. **Dashboard integration** — metrics feed into Athanor's dashboard (ADR-007) and detailed views in Grafana
6. **Always-on** — monitoring must run 24/7 on VAULT (ADR-004)
7. **One-person maintainable** — no complex distributed tracing or log aggregation. Simple, understandable.

---

## The Standard Stack

This is not a research question with multiple viable candidates. The monitoring stack for Docker-based homelabs is well-established:

### Prometheus — Metrics Collection

Time-series database that scrapes metrics from exporters at configurable intervals. Pull-based model — Prometheus pulls from targets, targets don't push.

### Grafana — Visualization

Dashboard tool that queries Prometheus (and other data sources) and renders graphs, tables, gauges. Extensive pre-built dashboard library.

### Exporters — Data Sources

| Exporter | Metrics | Where It Runs |
|----------|---------|---------------|
| **node_exporter** | CPU, RAM, disk, network, filesystem | Node 1, Node 2 (Docker) |
| **Unraid Prometheus plugin** | CPU, RAM, disk, array status | VAULT (Unraid plugin) |
| **dcgm-exporter** | GPU utilization, VRAM, temp, power, clock speeds | Node 1, Node 2 (Docker) |
| **cAdvisor** | Docker container metrics (CPU, memory, network per container) | Node 1, Node 2 (Docker) |
| **vLLM metrics** | Inference throughput, latency, queue depth, KV cache usage | Node 1, Node 2 (vLLM built-in) |

### Alertmanager — Alerting

Handles alerts from Prometheus. Can send to email, Slack, Discord, webhooks. Rules like "GPU temp > 85°C for 5 minutes" or "disk usage > 90%".

---

## No Alternatives Seriously Considered

| Alternative | Why Not |
|-------------|---------|
| InfluxDB + Telegraf | Valid stack, but Prometheus has better GPU/Docker exporter ecosystem. Grafana works with both — no advantage to switching. |
| Datadog / New Relic | Cloud SaaS. Costs money, sends data off-network. No reason when Prometheus is free and runs locally. |
| Zabbix | Enterprise-oriented, heavier than needed for 4 machines. |
| Just nvidia-smi | No history, no dashboards, no alerting. Fine for spot checks, not monitoring. |

Prometheus + Grafana is the default for Docker homelabs. The question isn't whether to use it, but how to configure it for Athanor's specific needs.

---

## GPU Monitoring: DCGM-Exporter

NVIDIA's Data Center GPU Manager (DCGM) exporter provides GPU metrics to Prometheus. Runs as a Docker container:

```bash
docker run -d --gpus all --cap-add SYS_ADMIN \
  -p 9400:9400 \
  nvcr.io/nvidia/k8s/dcgm-exporter:4.5.2-4.8.1-distroless
```

Metrics include:
- `DCGM_FI_DEV_GPU_UTIL` — GPU utilization %
- `DCGM_FI_DEV_FB_USED` — Framebuffer (VRAM) used
- `DCGM_FI_DEV_FB_FREE` — Framebuffer (VRAM) free
- `DCGM_FI_DEV_GPU_TEMP` — GPU temperature
- `DCGM_FI_DEV_POWER_USAGE` — Power draw (watts)
- `DCGM_FI_DEV_SM_CLOCK` — SM clock speed
- `DCGM_FI_DEV_MEM_CLOCK` — Memory clock speed

Pre-built Grafana dashboard: [Dashboard #12239](https://grafana.com/grafana/dashboards/12239-nvidia-dcgm-exporter-dashboard/)

**Sources:**
- [DCGM-Exporter GitHub](https://github.com/NVIDIA/dcgm-exporter)
- [DCGM-Exporter documentation](https://docs.nvidia.com/datacenter/dcgm/latest/gpu-telemetry/dcgm-exporter.html)
- [vLLM + DCGM monitoring guide](https://medium.com/@kimdoil1211/how-to-monitor-gpu-cpu-and-memory-usage-of-a-vllm-server-using-prometheus-dcgm-exporter-f988afd70460)

## vLLM Built-in Metrics

vLLM exposes Prometheus metrics natively on its metrics endpoint:
- Request throughput (tokens/sec)
- Request latency (time to first token, total generation time)
- Queue depth (pending requests)
- KV cache utilization
- GPU memory usage per model

No additional exporter needed — Prometheus scrapes vLLM directly.

## Unraid Monitoring

The Prometheus Node Exporter plugin for Unraid (v2025.02.17, based on node_exporter v1.9.0) exports system metrics at `http://VAULT_IP:9100/metrics`.

Install via Community Apps (CA). Provides CPU, RAM, disk, network, and filesystem metrics for the Unraid host.

For array-specific metrics (disk health, parity status, share usage), the Unraid SNMP plugin or custom scripts can feed additional data.

**Sources:**
- [Unraid Prometheus monitoring guide](https://unraid.net/blog/prometheus)
- [Unraid Prometheus node_exporter plugin](https://github.com/ich777/unraid-prometheus_node_exporter)

---

## Recommendation

### Prometheus + Grafana on VAULT, exporters on all nodes.

```
VAULT (always-on):
  ├── Prometheus (port 9090)     ← scrapes all targets
  ├── Grafana (port 3000)        ← dashboards and alerting
  ├── Alertmanager (port 9093)   ← alert routing
  └── node_exporter (port 9100)  ← VAULT system metrics (plugin)

Node 1:
  ├── node_exporter (port 9100)  ← system metrics
  ├── dcgm-exporter (port 9400)  ← GPU metrics (4x 5070 Ti)
  ├── cAdvisor (port 8080)       ← container metrics
  └── vLLM metrics endpoint      ← inference metrics

Node 2:
  ├── node_exporter (port 9100)  ← system metrics
  ├── dcgm-exporter (port 9400)  ← GPU metrics (5090 + 4090)
  ├── cAdvisor (port 8080)       ← container metrics
  └── vLLM metrics endpoint      ← inference metrics
```

Prometheus on VAULT scrapes all targets every 15 seconds. Grafana on VAULT visualizes everything. Athanor's custom dashboard (ADR-007) queries Prometheus's API for summary metrics.
