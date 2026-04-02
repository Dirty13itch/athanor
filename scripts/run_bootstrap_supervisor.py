from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _ensure_import_path() -> None:
    agents_src = _repo_root() / "projects" / "agents" / "src"
    if str(agents_src) not in sys.path:
        sys.path.insert(0, str(agents_src))


async def _run(
    program_id: str,
    *,
    execute: bool,
    retry_blockers: bool,
    process_integrations: bool,
) -> dict[str, object]:
    from athanor_agents.bootstrap_state import run_bootstrap_supervisor_cycle

    return await run_bootstrap_supervisor_cycle(
        program_id=program_id,
        execute=execute,
        retry_blockers=retry_blockers,
        process_integrations=process_integrations,
    )


async def _run_loop(
    program_id: str,
    *,
    interval_seconds: int,
    max_cycles: int | None,
    execute: bool,
    retry_blockers: bool,
    process_integrations: bool,
) -> dict[str, object]:
    from athanor_agents.bootstrap_state import run_bootstrap_supervisor_loop

    return await run_bootstrap_supervisor_loop(
        program_id=program_id,
        interval_seconds=interval_seconds,
        max_cycles=max_cycles,
        execute=execute,
        retry_blockers=retry_blockers,
        process_integrations=process_integrations,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Athanor bootstrap supervisor cycles.")
    parser.add_argument("--program-id", default="", help="Optional bootstrap program id to scope the cycle.")
    parser.add_argument("--json", action="store_true", help="Emit the full cycle payload as JSON.")
    parser.add_argument("--execute", action="store_true", help="Perform mutable bootstrap actions instead of recommendation-only cycles.")
    parser.add_argument("--loop", action="store_true", help="Run the supervisor as a repeating loop instead of a single cycle.")
    parser.add_argument("--interval-seconds", type=int, default=600, help="Loop interval in seconds when --loop is set.")
    parser.add_argument("--max-cycles", type=int, default=1, help="Maximum cycles to run when --loop is set.")
    parser.add_argument("--skip-retry-blockers", action="store_true", help="Skip retrying eligible bootstrap blockers during the cycle.")
    parser.add_argument("--skip-integrations", action="store_true", help="Skip processing the bootstrap integration queue during the cycle.")
    args = parser.parse_args()

    _ensure_import_path()
    if args.loop:
        result = asyncio.run(
            _run_loop(
                args.program_id,
                interval_seconds=max(int(args.interval_seconds), 1),
                max_cycles=max(int(args.max_cycles), 1),
                execute=bool(args.execute),
                retry_blockers=not bool(args.skip_retry_blockers),
                process_integrations=not bool(args.skip_integrations),
            )
        )
    else:
        result = asyncio.run(
            _run(
                args.program_id,
                execute=bool(args.execute),
                retry_blockers=not bool(args.skip_retry_blockers),
                process_integrations=not bool(args.skip_integrations),
            )
        )
    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    if args.loop:
        print(f"loop_completed_at={result.get('loop_completed_at', '')}")
        print(f"cycle_count={result.get('cycle_count', 0)}")
        last_cycle = result.get("last_cycle") or {}
        print(f"active_program_id={last_cycle.get('active_program_id', '')}")
        print(f"active_family={last_cycle.get('active_family', '')}")
        recommendation = last_cycle.get("recommendation") or {}
        print(f"recommended_slice={recommendation.get('slice_id', '')}")
        print(f"recommended_host={recommendation.get('host_id', '')}")
        print(f"actions={len(last_cycle.get('actions', []))}")
        return 0

    recommendation = result.get("recommendation") or {}
    print(f"generated_at={result.get('generated_at', '')}")
    print(f"active_program_id={result.get('active_program_id', '')}")
    print(f"active_family={result.get('active_family', '')}")
    print(f"recommended_slice={recommendation.get('slice_id', '')}")
    print(f"recommended_host={recommendation.get('host_id', '')}")
    print(f"ready={recommendation.get('ready', False)}")
    print(f"execute={result.get('execute', False)}")
    print(f"actions={len(result.get('actions', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
