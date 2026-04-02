# Model Lane Outage

Source of truth: provider routing posture, model governance, and `/health`

---

## Trigger

- local model lane unavailable
- frontier API lane degraded or auth-failed
- routing policy no longer has a safe worker for the workload

## Sequence

1. Confirm whether the lane is local, frontier-cloud, or handoff-only.
2. Keep sovereign-only work on sovereign lanes even if throughput drops.
3. Reroute cloud-safe work only to allowed fallback lanes.
4. Do not silently widen privacy posture to bypass the outage.
5. Capture provider evidence before closing the incident.

## Verify

- affected workloads have a safe fallback or remain blocked by policy
- no sovereign workload leaked onto cloud lanes
- provider evidence reflects the outage or repair
