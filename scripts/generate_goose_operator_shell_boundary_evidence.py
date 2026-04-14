#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "config" / "automation-backbone"
OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "goose-boundary-evidence.md"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _find_record(records: list[dict[str, Any]], key: str, value: str) -> dict[str, Any]:
    for record in records:
        if isinstance(record, dict) and str(record.get(key) or "").strip() == value:
            return dict(record)
    return {}


def _load_mcp_allowlist() -> list[str]:
    settings_path = REPO_ROOT / ".claude" / "settings.json"
    payload = _load_json(settings_path)
    permissions = dict(payload.get("permissions") or {})
    return [
        str(item).strip()
        for item in permissions.get("allow", [])
        if str(item).strip().startswith("mcp__")
    ]


def _format_bullets(items: list[str]) -> str:
    if not items:
        return "- none"
    return "\n".join(f"- {item}" for item in items)


def main() -> int:
    lane_selection = _load_json(CONFIG_DIR / "lane-selection-matrix.json")
    operator_surfaces = _load_json(CONFIG_DIR / "operator-surface-registry.json")
    failure_routing = _load_json(CONFIG_DIR / "failure-routing-matrix.json")
    runtime_packets = _load_json(CONFIG_DIR / "runtime-ownership-packets.json")
    eval_ledger = _load_json(CONFIG_DIR / "eval-run-ledger.json")

    goose_mode = _find_record(
        [dict(item) for item in lane_selection.get("execution_mode_defaults", []) if isinstance(item, dict)],
        "mode",
        "goose_wrapped",
    )
    repo_audit_profile = _find_record(
        [dict(item) for item in lane_selection.get("selection_profiles", []) if isinstance(item, dict)],
        "task_class",
        "repo_wide_audit",
    )
    goose_surface = _find_record(
        [dict(item) for item in operator_surfaces.get("surfaces", []) if isinstance(item, dict)],
        "id",
        "desk_goose_operator_shell",
    )
    goose_packet = _find_record(
        [dict(item) for item in runtime_packets.get("packets", []) if isinstance(item, dict)],
        "id",
        "desk-goose-operator-shell-rollout-packet",
    )
    goose_eval = _find_record(
        [dict(item) for item in eval_ledger.get("runs", []) if isinstance(item, dict)],
        "run_id",
        "goose-operator-shell-lane-eval-2026q2",
    )

    request_surface_hint = str(dict(goose_eval.get("execution_requirements") or {}).get("request_surface_hint") or "").strip()
    mcp_allowlist = _load_mcp_allowlist()
    failure_rows = [
        row
        for row in failure_routing.get("rows", [])
        if isinstance(row, dict)
        and str(row.get("failure_class") or "").strip() in {"litellm_degraded", "cluster_degraded_mode"}
    ]

    missing_evidence: list[str] = []
    if str(repo_audit_profile.get("default_execution_mode") or "").strip() != "goose_wrapped":
        missing_evidence.append("repo_wide_audit no longer defaults to goose_wrapped")
    if "multi_step_orchestration" not in list(goose_mode.get("use_for") or []):
        missing_evidence.append("goose_wrapped execution-mode defaults no longer include multi_step_orchestration")
    if not request_surface_hint:
        missing_evidence.append("Goose eval run no longer declares a dashboard-routed request surface")
    if str(goose_surface.get("mcp_extension_policy") or "").strip() != "deny_by_default_until_allowlist_evidence_lands":
        missing_evidence.append("Goose operator surface is no longer deny-by-default for MCP extensions")
    if not mcp_allowlist:
        missing_evidence.append("No MCP namespaces are allowlisted in .claude/settings.json")
    if not str(goose_surface.get("fallback_operator_path") or "").strip():
        missing_evidence.append("Goose operator surface no longer declares an explicit fallback operator path")
    if not failure_rows:
        missing_evidence.append("Failure-routing matrix no longer carries the Goose-relevant degraded fallbacks")

    generated_at = datetime.now(timezone.utc).isoformat()
    packet_status = str(goose_packet.get("status") or "").strip() or "unknown"
    packet_approval_type = str(goose_packet.get("approval_packet_type") or "").strip() or "unknown"
    packet_goal = str(goose_packet.get("goal") or "").strip()
    fallback_path = str(goose_surface.get("fallback_operator_path") or "").strip()
    evidence_complete = not missing_evidence

    lines = [
        "# Goose Boundary Evidence",
        "",
        f"Generated from current Goose truth surfaces on {generated_at}.",
        "",
        "This artifact is a synthesis of current repo truth. It does not claim a new runtime eval; it records the shell-boundary, MCP policy, and fallback evidence for the adopted bounded Goose shell path.",
        "",
        "## Dashboard-Routed Shell Evidence",
        "",
        f"- Pilot eval run: `goose-operator-shell-lane-eval-2026q2`",
        f"- Request surface hint: `{request_surface_hint or 'missing'}`",
        f"- Wrapper mode: `{str(goose_eval.get('wrapper_mode') or '').strip() or 'missing'}`",
        f"- Operator test flow: `{str(goose_eval.get('operator_test_flow_id') or '').strip() or 'missing'}`",
        f"- Repo-wide audit default execution mode: `{str(repo_audit_profile.get('default_execution_mode') or '').strip() or 'missing'}`",
        f"- Goose execution-mode use cases: `{', '.join(str(item).strip() for item in goose_mode.get('use_for', []) if str(item).strip()) or 'missing'}`",
        f"- Packet target surface: `{str(goose_packet.get('goal') or '').strip() or 'missing'}`",
        "",
        "This shows Goose being evaluated as a dashboard-routed bounded shell path, not as a second control plane.",
        "",
        "## MCP Allowlist Proof",
        "",
        f"- Operator-surface MCP policy: `{str(goose_surface.get('mcp_extension_policy') or '').strip() or 'missing'}`",
        f"- Allowed MCP extensions on the Goose surface: `{', '.join(str(item).strip() for item in goose_surface.get('allowed_mcp_extensions', []) if str(item).strip()) or '[]'}`",
        "- Local MCP namespace allowlist from `C:/Athanor/.claude/settings.json`:",
        _format_bullets(mcp_allowlist),
        "",
        "The local operator surface stays deny-by-default for Goose-specific extension use until explicit allowlist evidence and future shell-path packet changes say otherwise.",
        "",
        "## Failure-Fallback Proof",
        "",
        f"- Rollout packet id: `{str(goose_packet.get('id') or '').strip() or 'missing'}`",
        f"- Rollout packet status: `{packet_status}`",
        f"- Approval packet type: `{packet_approval_type}`",
        f"- Packet goal: `{packet_goal or 'missing'}`",
        f"- Fallback operator path: `{fallback_path or 'missing'}`",
        "- Relevant degraded fallback rows from `failure-routing-matrix.json`:",
    ]

    if failure_rows:
        for row in failure_rows:
            allowed_fallbacks = ", ".join(
                str(item).strip() for item in row.get("allowed_fallbacks", []) if str(item).strip()
            )
            blocked_workloads = ", ".join(
                str(item).strip() for item in row.get("blocked_workloads", []) if str(item).strip()
            )
            lines.append(
                f"- `{str(row.get('failure_class') or '').strip()}` -> fallbacks `{allowed_fallbacks or 'none'}`; blocked workloads `{blocked_workloads or 'none'}`"
            )
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Closure Status",
            "",
            f"- Evidence complete: `{str(evidence_complete).lower()}`",
            f"- Source-safe gaps: `{len(missing_evidence)}`",
        ]
    )
    if missing_evidence:
        lines.append("- Remaining evidence gaps:")
        lines.append(_format_bullets(missing_evidence))
    else:
        lines.append("- The concrete boundary evidence is captured here.")
        if packet_status == "executed":
            lines.append("- The rollout packet is executed, so the remaining Goose work is bounded maintenance and future packet-backed shell-path changes.")
        else:
            lines.append("- The remaining Goose gate is packet review plus the existing approval boundary, not more source-safe evidence collection.")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(str(OUTPUT_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
