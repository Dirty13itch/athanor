from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _ensure_import_path() -> None:
    agents_src = _repo_root() / "projects" / "agents" / "src"
    if str(agents_src) not in sys.path:
        sys.path.insert(0, str(agents_src))


def _print_json(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, indent=2))
    return 0


def _normalize_csv_list(values: list[str] | None) -> list[str]:
    normalized: list[str] = []
    for value in values or []:
        for item in str(value).split(","):
            candidate = item.strip()
            if candidate:
                normalized.append(candidate)
    return normalized


async def _run_status(args: argparse.Namespace) -> dict[str, Any]:
    from athanor_agents.bootstrap_state import (
        build_bootstrap_runtime_snapshot,
        get_bootstrap_program_detail,
        list_bootstrap_host_states,
    )

    snapshot = await build_bootstrap_runtime_snapshot()
    hosts = await list_bootstrap_host_states()
    if args.host_id:
        hosts = [host for host in hosts if str(host.get("id") or "") == args.host_id]
    program = await get_bootstrap_program_detail(args.program_id) if args.program_id else None
    return {
        "generated_at": snapshot.get("last_updated_at", ""),
        "status": snapshot,
        "hosts": hosts,
        "program": program,
    }


async def _run_claim_next(args: argparse.Namespace) -> dict[str, Any]:
    from athanor_agents.bootstrap_runtime import claim_next_bootstrap_slice_for_host

    result = await claim_next_bootstrap_slice_for_host(
        args.host_id,
        program_id=args.program_id,
        execute=bool(args.execute),
    )
    return {"status": "claimed" if args.execute else "planned", **result}


async def _run_relay(args: argparse.Namespace) -> dict[str, Any]:
    from athanor_agents.bootstrap_runtime import relay_bootstrap_slice_for_host

    return await relay_bootstrap_slice_for_host(
        args.host_id,
        slice_id=args.slice_id,
        stop_reason=args.stop_reason,
        cooldown_minutes=args.cooldown_minutes,
        execute=bool(args.execute),
        blocker_class=args.blocker_class,
        approval_required=bool(args.approval_required),
    )


async def _run_complete(args: argparse.Namespace) -> dict[str, Any]:
    from athanor_agents.bootstrap_state import complete_bootstrap_slice

    result = await complete_bootstrap_slice(
        args.slice_id,
        host_id=args.host_id,
        current_ref=args.current_ref,
        worktree_path=args.worktree_path,
        files_touched=_normalize_csv_list(args.files_touched),
        validation_status=args.validation_status,
        open_risks=_normalize_csv_list(args.open_risks),
        next_step=args.next_step,
        summary=args.summary,
        integration_method=args.integration_method,
        target_ref=args.target_ref,
        queue_priority=args.queue_priority,
    )
    return {"status": "completed", **result}


async def _run_host_status(args: argparse.Namespace) -> dict[str, Any]:
    from athanor_agents.bootstrap_state import update_bootstrap_host_status

    host_state = await update_bootstrap_host_status(
        args.host_id,
        status=args.status,
        active_slice_id=args.active_slice_id,
        last_reason=args.last_reason,
        cooldown_minutes=args.cooldown_minutes,
        metadata={"adapter": "bootstrap_host_adapter", "note": args.note} if args.note else {"adapter": "bootstrap_host_adapter"},
    )
    return {"status": "updated", "host": host_state}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Athanor bootstrap host adapter commands.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="Inspect bootstrap host/program posture.")
    status.add_argument("--host-id", default="", help="Optional host id filter.")
    status.add_argument("--program-id", default="", help="Optional program id to include in the payload.")
    status.add_argument("--json", action="store_true", help="Emit the full payload as JSON.")

    claim_next = subparsers.add_parser("claim-next", help="Claim the next eligible bootstrap slice for a host.")
    claim_next.add_argument("--host-id", required=True, help="Bootstrap host id claiming the slice.")
    claim_next.add_argument("--program-id", default="", help="Optional program id to scope the claim.")
    claim_next.add_argument("--execute", action="store_true", help="Materialize the worktree and persist the claim.")
    claim_next.add_argument("--json", action="store_true", help="Emit the full payload as JSON.")

    relay = subparsers.add_parser("relay", help="Relay a claimed bootstrap slice to the next available host.")
    relay.add_argument("--host-id", required=True, help="Current bootstrap host id.")
    relay.add_argument("--slice-id", default="", help="Optional slice id. Defaults to the host's active slice.")
    relay.add_argument("--stop-reason", default="session_exhausted", help="Relay reason such as session_exhausted.")
    relay.add_argument("--cooldown-minutes", type=int, default=30, help="Cooldown window for the relinquishing host.")
    relay.add_argument("--blocker-class", default="", help="Optional blocker class to record during relay.")
    relay.add_argument("--approval-required", action="store_true", help="Mark the relay blocker as approval gated.")
    relay.add_argument("--execute", action="store_true", help="Persist the relay instead of returning a plan.")
    relay.add_argument("--json", action="store_true", help="Emit the full payload as JSON.")

    complete = subparsers.add_parser("complete", help="Complete a bootstrap slice from the host lane.")
    complete.add_argument("--slice-id", required=True, help="Bootstrap slice id.")
    complete.add_argument("--host-id", default="", help="Host completing the slice.")
    complete.add_argument("--current-ref", default="", help="Current git ref or commit for the slice.")
    complete.add_argument("--worktree-path", default="", help="Existing worktree path for the slice.")
    complete.add_argument("--files-touched", nargs="*", default=[], help="Touched files, space- or comma-separated.")
    complete.add_argument("--open-risks", nargs="*", default=[], help="Open risks, space- or comma-separated.")
    complete.add_argument("--validation-status", default="passed", help="Validation result for the slice.")
    complete.add_argument("--next-step", default="", help="Next step note to retain on the slice.")
    complete.add_argument("--summary", default="", help="Summary recorded alongside the validation bundle.")
    complete.add_argument("--integration-method", default="squash_commit", help="Replay method for the serial integration lane.")
    complete.add_argument("--target-ref", default="main", help="Integration target ref.")
    complete.add_argument("--queue-priority", type=int, default=3, help="Integration queue priority.")
    complete.add_argument("--json", action="store_true", help="Emit the full payload as JSON.")

    host_status = subparsers.add_parser("host-status", help="Update bootstrap host posture without claiming or relaying.")
    host_status.add_argument("--host-id", required=True, help="Bootstrap host id.")
    host_status.add_argument("--status", required=True, help="New host status.")
    host_status.add_argument("--active-slice-id", default="", help="Optional active slice id.")
    host_status.add_argument("--last-reason", default="", help="Reason recorded on the host state.")
    host_status.add_argument("--cooldown-minutes", type=int, default=0, help="Cooldown period when applicable.")
    host_status.add_argument("--note", default="", help="Optional adapter note stored in metadata.")
    host_status.add_argument("--json", action="store_true", help="Emit the full payload as JSON.")

    return parser


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    _ensure_import_path()

    handlers = {
        "status": _run_status,
        "claim-next": _run_claim_next,
        "relay": _run_relay,
        "complete": _run_complete,
        "host-status": _run_host_status,
    }
    result = asyncio.run(handlers[args.command](args))
    if getattr(args, "json", False):
        return _print_json(result)

    if args.command == "status":
        hosts = result.get("hosts") or []
        program = result.get("program") or {}
        status = result.get("status") or {}
        print(f"active_program_id={status.get('active_program_id', '')}")
        print(f"active_family={status.get('active_family', '')}")
        print(f"open_blockers={status.get('open_blockers', 0)}")
        print(f"pending_integrations={status.get('pending_integrations', 0)}")
        print(f"host_count={len(hosts)}")
        if program:
            print(f"program_id={program.get('id', '')}")
            print(f"next_slice_id={program.get('next_slice_id', '')}")
            print(f"recommended_host_id={program.get('recommended_host_id', '')}")
        return 0

    if args.command == "claim-next":
        slice_record = result.get("slice") or {}
        worktree = result.get("worktree") or {}
        print(f"program_id={result.get('program_id', '')}")
        print(f"slice_id={slice_record.get('id', '')}")
        print(f"host_id={slice_record.get('host_id', '')}")
        print(f"worktree_path={worktree.get('worktree_path', '')}")
        print(f"contract_path={result.get('contract_path', '')}")
        return 0

    if args.command == "relay":
        slice_record = result.get("slice") or {}
        print(f"status={result.get('status', '')}")
        print(f"slice_id={slice_record.get('id', '')}")
        print(f"from_host_id={result.get('from_host_id', '')}")
        print(f"to_host_id={result.get('to_host_id', '')}")
        print(f"stop_reason={result.get('stop_reason', '')}")
        if result.get("contract_path"):
            print(f"contract_path={result.get('contract_path', '')}")
        if result.get("blocker", {}).get("id"):
            print(f"blocker_id={result.get('blocker', {}).get('id', '')}")
        return 0

    if args.command == "complete":
        slice_record = result.get("slice") or {}
        integration = result.get("integration") or {}
        print(f"slice_id={slice_record.get('id', '')}")
        print(f"status={slice_record.get('status', '')}")
        print(f"validation_status={slice_record.get('validation_status', '')}")
        print(f"integration_id={integration.get('id', '')}")
        return 0

    host = result.get("host") or {}
    print(f"host_id={host.get('id', '')}")
    print(f"status={host.get('status', '')}")
    print(f"active_slice_id={host.get('active_slice_id', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
