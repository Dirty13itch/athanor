#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from routing_contract_support import append_history, dump_json, load_json, parse_dt


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "config" / "automation-backbone"
OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "capacity-telemetry.json"
SCHEDULER_EVAL_PATHS = [
    REPO_ROOT / "reports" / "truth-inventory" / "gpu-scheduler-promotion-eval.json",
    REPO_ROOT / "reports" / "truth-inventory" / "gpu-scheduler-baseline-eval.json",
]

NODE_TO_SCHEDULER_NODE = {
    "foundry": "node1",
    "workshop": "node2",
    "dev": "node3",
}

GPU_TO_SCHEDULER_SLOT = {
    "dev-rtx5060ti": "D:0",
    "foundry-rtx4090": "F:2",
    "foundry-rtx5070ti-a": "F:TP4",
    "foundry-rtx5070ti-b": "F:TP4",
    "foundry-rtx5070ti-c": "F:TP4",
    "foundry-rtx5070ti-d": "F:TP4",
    "workshop-rtx5090": "W:0",
    "workshop-rtx5060ti": "W:1",
}

LIVE_IDLE_SLOT_STATES = {"IDLE", "SLEEPING_L1"}
LIVE_BUSY_SLOT_STATES = {"ACTIVE", "PRELOADING", "RELEASING"}


def _slot_zone_id(scheduler_slot_id: str | None) -> str | None:
    raw = str(scheduler_slot_id or "").strip()
    if not raw or ":" not in raw:
        return None
    return raw.split(":", 1)[0]


def _load_slot_target_index(capacity: dict[str, Any]) -> dict[str, dict[str, Any]]:
    targets: dict[str, dict[str, Any]] = {}
    for target in capacity.get("scheduler_slot_targets", []):
        if not isinstance(target, dict):
            continue
        scheduler_slot_id = str(target.get("scheduler_slot_id") or "").strip()
        if not scheduler_slot_id:
            continue
        targets[scheduler_slot_id] = dict(target)
    return targets


def _freshness_seconds(raw: str | None) -> int | None:
    parsed = parse_dt(raw)
    if parsed is None:
        return None
    return max(0, int((datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds()))


def _load_scheduler_projection() -> tuple[dict[str, Any], str | None]:
    freshest_payload: dict[str, Any] = {}
    freshest_source: str | None = None
    freshest_observed_at: datetime | None = None
    for path in SCHEDULER_EVAL_PATHS:
        if not path.exists():
            continue
        try:
            payload = load_json(path)
        except Exception:
            continue
        body = dict(dict(payload.get("live_scheduler_state") or {}).get("body") or {})
        if not body:
            body = dict(payload.get("scheduler_state") or {})
        if not body:
            body = dict(dict(dict(payload.get("live_runtime") or {}).get("scheduler_state") or {}).get("body") or {})
        if not (isinstance(body.get("gpus"), dict) and body["gpus"]):
            continue
        observed_at = (
            parse_dt(body.get("timestamp"))
            or parse_dt(payload.get("generated_at"))
            or datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        )
        if freshest_observed_at is None or observed_at > freshest_observed_at:
            freshest_payload = body
            freshest_source = path.relative_to(REPO_ROOT).as_posix()
            freshest_observed_at = observed_at
    return freshest_payload, freshest_source


def _projection_utilization_percent(slot: dict[str, Any]) -> int:
    state = str(slot.get("state") or "").strip().upper()
    vram_total_mb = int(slot.get("vram_total_mb") or 0)
    vram_used_mb = int(slot.get("vram_used_mb") or 0)
    if state in LIVE_IDLE_SLOT_STATES:
        return 0
    if vram_total_mb <= 0:
        return 35 if state in LIVE_BUSY_SLOT_STATES else 10
    return max(0, min(100, round((vram_used_mb / vram_total_mb) * 100)))


def _is_harvest_target(node: dict[str, Any], *, protected: bool) -> bool:
    if protected:
        return False
    return int(node.get("background_fill_gpu_slots") or 0) > 0


def _scheduler_idle_window_open(
    slot: dict[str, Any],
    *,
    scheduler_queue_depth: int,
    harvest_target: bool,
    protected: bool,
) -> tuple[bool, str]:
    if protected:
        return False, "protected_reserve"
    if not harvest_target:
        return False, "not_harvest_target"
    if scheduler_queue_depth > 0:
        return False, "scheduler_queue_backlog"
    slot_state = str(slot.get("state") or "").strip().upper()
    if slot_state in LIVE_IDLE_SLOT_STATES:
        return True, "scheduler_idle_window"
    if slot_state in LIVE_BUSY_SLOT_STATES:
        return False, "active_runtime"
    return False, "scheduler_state_unavailable"


def main() -> int:
    contract = load_json(CONFIG_DIR / "capacity-telemetry-contract.json")
    capacity = load_json(CONFIG_DIR / "capacity-envelope-registry.json")
    hardware = load_json(CONFIG_DIR / "hardware-inventory.json")
    models = load_json(CONFIG_DIR / "model-deployment-registry.json")
    scheduler_projection, scheduler_source = _load_scheduler_projection()

    hardware_by_node = {
        str(node.get("id") or "").strip(): dict(node)
        for node in hardware.get("nodes", [])
        if isinstance(node, dict) and str(node.get("id") or "").strip()
    }
    lanes_by_node: dict[str, list[dict[str, Any]]] = {}
    for lane in models.get("lanes", []):
        if not isinstance(lane, dict):
            continue
        node_id = str(lane.get("node_id") or "").strip()
        if not node_id:
            continue
        lanes_by_node.setdefault(node_id, []).append(dict(lane))

    node_samples: list[dict[str, Any]] = []
    gpu_samples: list[dict[str, Any]] = []
    queue_samples: list[dict[str, Any]] = []
    idle_windows: list[dict[str, Any]] = []
    harvest_admission: list[dict[str, Any]] = []
    scheduler_slot_samples: list[dict[str, Any]] = []

    protected_reserves = set(contract.get("protected_reserves", []))
    slot_targets = _load_slot_target_index(capacity)
    scheduler_gpus = dict(scheduler_projection.get("gpus") or {})
    scheduler_timestamp = str(scheduler_projection.get("timestamp") or "").strip() or None
    scheduler_queue_depth = int(scheduler_projection.get("queue_depth") or 0)
    scheduler_active_transitions = int(scheduler_projection.get("active_transitions") or 0)
    scheduler_write_capabilities = dict(scheduler_projection.get("write_capabilities") or {})

    for node in capacity.get("nodes", []):
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("node_id") or "").strip()
        if not node_id:
            continue
        hardware_node = hardware_by_node.get(node_id, {})
        observed = dict(node.get("observed_telemetry") or {})
        busy_roles = {str(item) for item in observed.get("busy_gpu_roles", [])}
        idle_roles = {str(item) for item in observed.get("idle_gpu_roles", [])}
        scheduler_node_id = NODE_TO_SCHEDULER_NODE.get(node_id)
        node_scheduler_slots = [
            dict(slot)
            for slot in scheduler_gpus.values()
            if isinstance(slot, dict) and str(slot.get("node") or "").strip() == scheduler_node_id
        ]
        node_sample_source = observed.get("source")
        node_sample_state = "registry_seed"
        node_observed_at = observed.get("last_verified_at")
        if node_scheduler_slots and scheduler_source:
            node_sample_source = scheduler_source
            node_sample_state = "live_projection"
            node_observed_at = scheduler_timestamp
        node_samples.append(
            {
                "node_id": node_id,
                "node_role": node.get("node_role"),
                "host": hardware_node.get("host"),
                "cpu_model": dict(hardware_node.get("cpu") or {}).get("model"),
                "ram_gb": hardware_node.get("ram_gb"),
                "storage_tb_total": sum(
                    float(item.get("size_tb") or 0)
                    for item in hardware_node.get("storage", [])
                        if isinstance(item, dict)
                ),
                "observed_at": node_observed_at,
                "freshness_seconds": _freshness_seconds(node_observed_at),
                "sample_source": node_sample_source,
                "sample_state": node_sample_state,
                "interactive_reserve_preserved": bool(observed.get("interactive_reserve_preserved")),
                "background_fill_gpu_slots": node.get("background_fill_gpu_slots"),
                "interactive_reserve_gpu_slots": node.get("interactive_reserve_gpu_slots"),
                "scheduler_queue_depth": scheduler_queue_depth if node_scheduler_slots else 0,
                "scheduler_backed_gpu_slots": len(node_scheduler_slots),
            }
        )

        for gpu in node.get("gpus", []):
            if not isinstance(gpu, dict):
                continue
            gpu_id = str(gpu.get("gpu_id") or "").strip()
            owner_lane = str(gpu.get("owner_lane") or "")
            is_idle = owner_lane in idle_roles
            is_busy = owner_lane in busy_roles
            protected = gpu_id in protected_reserves
            scheduler_slot_id = GPU_TO_SCHEDULER_SLOT.get(gpu_id)
            scheduler_zone_id = _slot_zone_id(scheduler_slot_id)
            slot_target = dict(slot_targets.get(str(scheduler_slot_id or "").strip()) or {})
            scheduler_slot = dict(scheduler_gpus.get(scheduler_slot_id) or {}) if scheduler_slot_id else {}
            if scheduler_slot:
                utilization_percent = _projection_utilization_percent(scheduler_slot)
                queue_depth = scheduler_queue_depth
                oldest_wait_seconds = 0
                sample_source = scheduler_source
                sample_state = "live_projection"
                observed_at = scheduler_timestamp
                scheduler_state = str(scheduler_slot.get("state") or "").strip() or None
                projection_conflict = str(scheduler_slot.get("projection_conflict") or "").strip() or None
            else:
                utilization_percent = 0 if is_idle else 35 if is_busy else 10
                queue_depth = 0 if is_idle else 1 if is_busy else 0
                oldest_wait_seconds = 0 if is_idle else 45 if is_busy else 0
                sample_source = observed.get("source")
                sample_state = "registry_seed"
                observed_at = observed.get("last_verified_at")
                scheduler_state = None
                projection_conflict = None
            harvest_target = _is_harvest_target(node, protected=protected)
            gpu_samples.append(
                {
                    "node_id": node_id,
                    "gpu_id": gpu_id,
                    "model": gpu.get("model"),
                    "owner_lane": owner_lane,
                    "protected_reserve": protected,
                    "utilization_percent": utilization_percent,
                    "queue_depth": queue_depth,
                    "oldest_wait_seconds": oldest_wait_seconds,
                    "sample_source": sample_source,
                    "sample_state": sample_state,
                    "observed_at": observed_at,
                    "scheduler_slot_id": scheduler_slot_id,
                    "scheduler_zone_id": scheduler_zone_id,
                    "scheduler_state": scheduler_state,
                    "projection_conflict": projection_conflict,
                    "harvest_target": harvest_target,
                    "scheduler_slot_group_id": str(slot_target.get("id") or "").strip() or None,
                    "scheduler_slot_harvest_intent": str(slot_target.get("harvest_intent") or "").strip() or None,
                }
            )
            scheduler_backed = bool(scheduler_slot)
            provisional_harvest_candidate = False
            if scheduler_slot:
                idle_window_open, idle_reason = _scheduler_idle_window_open(
                    scheduler_slot,
                    scheduler_queue_depth=scheduler_queue_depth,
                    harvest_target=harvest_target,
                    protected=protected,
                )
            else:
                idle_window_open = (
                    not protected
                    and harvest_target
                    and is_idle
                    and bool(observed.get("interactive_reserve_preserved"))
                    and utilization_percent
                    < int(dict(contract.get("idle_window_rule") or {}).get("max_utilization_percent") or 20)
                )
                idle_reason = "idle_owner_lane" if idle_window_open else ("not_harvest_target" if not harvest_target else "busy_or_protected")
                provisional_harvest_candidate = idle_window_open
            harvest_admissible = idle_window_open if scheduler_backed else False
            idle_windows.append(
                {
                    "node_id": node_id,
                    "gpu_id": gpu_id,
                    "idle_window_open": idle_window_open,
                    "reason": idle_reason,
                    "scheduler_slot_id": scheduler_slot_id,
                    "scheduler_backed": scheduler_backed,
                    "provisional_harvest_candidate": provisional_harvest_candidate,
                }
            )
            harvest_admission.append(
                {
                    "node_id": node_id,
                    "gpu_id": gpu_id,
                    "harvest_admissible": harvest_admissible,
                    "blocked_by": (
                        []
                        if harvest_admissible
                        else (["requires_scheduler_backing"] if provisional_harvest_candidate else [idle_reason])
                    ),
                    "scheduler_slot_id": scheduler_slot_id,
                    "scheduler_zone_id": scheduler_zone_id,
                    "harvest_target": harvest_target,
                    "scheduler_slot_group_id": str(slot_target.get("id") or "").strip() or None,
                    "scheduler_slot_harvest_intent": str(slot_target.get("harvest_intent") or "").strip() or None,
                    "scheduler_backed": scheduler_backed,
                    "provisional_harvest_candidate": provisional_harvest_candidate,
                }
            )

        for lane in lanes_by_node.get(node_id, []):
            queue_samples.append(
                {
                    "lane_id": lane.get("id"),
                    "node_id": node_id,
                    "service_id": lane.get("service_id"),
                    "runtime_class": lane.get("runtime_class"),
                    "queue_depth": 1 if str(lane.get("state_class") or "") == "deployed" else 0,
                    "oldest_wait_seconds": 30 if str(lane.get("state_class") or "") == "deployed" else 0,
                    "observed_model_id": lane.get("observed_model_id"),
                    "observed_at": lane.get("verified_at"),
                    "sample_source": lane.get("evidence_source"),
                    "sample_state": "derived_assumption",
                    "queue_depth_source": "deployment_state_heuristic",
                }
            )

    harvestable_by_node: dict[str, int] = {}
    for record in harvest_admission:
        if not isinstance(record, dict) or not bool(record.get("harvest_admissible")):
            continue
        node_id = str(record.get("node_id") or "").strip()
        harvestable_by_node[node_id] = int(harvestable_by_node.get(node_id) or 0) + 1

    provisional_harvestable_by_node: dict[str, int] = {}
    for record in harvest_admission:
        if not isinstance(record, dict) or not bool(record.get("provisional_harvest_candidate")):
            continue
        node_id = str(record.get("node_id") or "").strip()
        provisional_harvestable_by_node[node_id] = int(provisional_harvestable_by_node.get(node_id) or 0) + 1

    harvest_admission_by_gpu = {
        str(record.get("gpu_id") or "").strip(): dict(record)
        for record in harvest_admission
        if isinstance(record, dict) and str(record.get("gpu_id") or "").strip()
    }
    harvestable_by_slot: dict[str, int] = {}
    harvestable_by_zone: dict[str, int] = {}
    slot_samples_by_id: dict[str, dict[str, Any]] = {}
    for sample in gpu_samples:
        if not isinstance(sample, dict):
            continue
        scheduler_slot_id = str(sample.get("scheduler_slot_id") or "").strip()
        gpu_id = str(sample.get("gpu_id") or "").strip()
        if not scheduler_slot_id or not gpu_id:
            continue
        scheduler_zone_id = _slot_zone_id(scheduler_slot_id)
        slot_target = dict(slot_targets.get(scheduler_slot_id) or {})
        slot_entry = slot_samples_by_id.setdefault(
            scheduler_slot_id,
            {
                "scheduler_slot_id": scheduler_slot_id,
                "scheduler_zone_id": scheduler_zone_id,
                "slot_target_id": str(slot_target.get("id") or "").strip() or None,
                "harvest_intent": str(slot_target.get("harvest_intent") or "").strip() or None,
                "node_ids": [],
                "member_gpu_ids": [],
                "admissible_gpu_ids": [],
                "blocked_by": [],
                "projection_conflicts": [],
                "harvestable_gpu_count": 0,
                "idle_window_open": False,
                "scheduler_state": None,
                "observed_at": sample.get("observed_at"),
                "sample_state": sample.get("sample_state"),
                "queue_depth": int(sample.get("queue_depth") or 0),
                "max_utilization_percent": int(sample.get("utilization_percent") or 0),
            },
        )
        node_id = str(sample.get("node_id") or "").strip()
        if node_id:
            slot_entry["node_ids"].append(node_id)
        slot_entry["member_gpu_ids"].append(gpu_id)
        slot_entry["queue_depth"] = max(int(slot_entry.get("queue_depth") or 0), int(sample.get("queue_depth") or 0))
        slot_entry["max_utilization_percent"] = max(
            int(slot_entry.get("max_utilization_percent") or 0),
            int(sample.get("utilization_percent") or 0),
        )
        scheduler_state = str(sample.get("scheduler_state") or "").strip()
        if scheduler_state:
            slot_entry["scheduler_state"] = scheduler_state
        projection_conflict = str(sample.get("projection_conflict") or "").strip()
        if projection_conflict:
            slot_entry["projection_conflicts"].append(projection_conflict)
        observed_at = str(sample.get("observed_at") or "").strip()
        if observed_at:
            current_observed_at = str(slot_entry.get("observed_at") or "").strip()
            if not current_observed_at or observed_at > current_observed_at:
                slot_entry["observed_at"] = observed_at
        admission = harvest_admission_by_gpu.get(gpu_id, {})
        if bool(admission.get("harvest_admissible")):
            slot_entry["idle_window_open"] = True
            slot_entry["admissible_gpu_ids"].append(gpu_id)
            harvestable_by_slot[scheduler_slot_id] = int(harvestable_by_slot.get(scheduler_slot_id) or 0) + 1
            if scheduler_zone_id:
                harvestable_by_zone[scheduler_zone_id] = int(harvestable_by_zone.get(scheduler_zone_id) or 0) + 1
        else:
            for blocked in admission.get("blocked_by", []) or []:
                blocked_reason = str(blocked or "").strip()
                if blocked_reason:
                    slot_entry["blocked_by"].append(blocked_reason)

    scheduler_slot_samples = []
    for scheduler_slot_id in sorted(slot_samples_by_id):
        slot_entry = dict(slot_samples_by_id[scheduler_slot_id])
        slot_entry["node_ids"] = sorted(set(slot_entry.get("node_ids") or []))
        slot_entry["member_gpu_ids"] = sorted(set(slot_entry.get("member_gpu_ids") or []))
        slot_entry["admissible_gpu_ids"] = sorted(set(slot_entry.get("admissible_gpu_ids") or []))
        slot_entry["blocked_by"] = sorted(set(slot_entry.get("blocked_by") or []))
        slot_entry["projection_conflicts"] = sorted(set(slot_entry.get("projection_conflicts") or []))
        slot_entry["harvestable_gpu_count"] = len(slot_entry["admissible_gpu_ids"])
        scheduler_slot_samples.append(slot_entry)

    snapshot = {
        "version": str(contract.get("version") or ""),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_of_truth": "reports/truth-inventory/capacity-telemetry.json",
        "contract_ref": "config/automation-backbone/capacity-telemetry-contract.json",
        "node_samples": node_samples,
        "gpu_samples": gpu_samples,
        "model_queue_samples": queue_samples,
        "idle_windows": idle_windows,
        "harvest_admission": harvest_admission,
        "scheduler_slot_samples": scheduler_slot_samples,
        "capacity_summary": {
            "sample_posture": "scheduler_projection_backed" if scheduler_source else "registry_seed_only",
            "scheduler_source": scheduler_source,
            "scheduler_observed_at": scheduler_timestamp,
            "scheduler_queue_depth": scheduler_queue_depth,
            "scheduler_active_transitions": scheduler_active_transitions,
            "scheduler_write_capabilities": scheduler_write_capabilities,
            "model_queue_truth_state": (
                "derived_assumption"
                if queue_samples
                else "unobserved"
            ),
            "node_sample_count": len(node_samples),
            "gpu_sample_count": len(gpu_samples),
            "scheduler_backed_gpu_count": sum(
                1 for sample in gpu_samples if str(sample.get("sample_state") or "") == "live_projection"
            ),
            "scheduler_conflict_gpu_count": sum(
                1 for sample in gpu_samples if str(sample.get("projection_conflict") or "").strip()
            ),
            "scheduler_slot_count": len(scheduler_slot_samples),
            "harvestable_scheduler_slot_count": sum(
                1 for sample in scheduler_slot_samples if bool(sample.get("idle_window_open"))
            ),
            "harvestable_gpu_count": sum(
                1 for record in harvest_admission if bool(record.get("harvest_admissible"))
            ),
            "provisional_harvest_candidate_count": sum(
                1 for record in harvest_admission if bool(record.get("provisional_harvest_candidate"))
            ),
            "harvestable_by_node": harvestable_by_node,
            "provisional_harvestable_by_node": provisional_harvestable_by_node,
            "harvestable_by_zone": harvestable_by_zone,
            "harvestable_by_slot": harvestable_by_slot,
        },
    }

    dump_json(OUTPUT_PATH, snapshot)
    append_history("capacity-telemetry", snapshot)
    print(OUTPUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
