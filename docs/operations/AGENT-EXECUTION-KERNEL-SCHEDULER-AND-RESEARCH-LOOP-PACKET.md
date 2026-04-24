# Agent Execution Kernel Scheduler and Research Loop Packet

## Objective

Bind the scheduler and research execution loop residue into one explicit publication slice so the execution-kernel family can rotate off queue-state closure and onto the remaining proving and support work.

## Scope

- `projects/agents/src/athanor_agents/research_jobs.py`
- `projects/agents/src/athanor_agents/scheduler.py`
- `projects/agents/src/athanor_agents/work_pipeline.py`
- `projects/agents/tests/test_research_jobs.py`
- `projects/agents/tests/test_scheduler.py`
- `projects/agents/tests/test_work_pipeline.py`

## Why This Exists

- `agent-execution-kernel-follow-on` now points at `scheduler-and-research-loop` as the next bounded target.
- These files are one coherent lane: scheduler admission, research loop recurrence, and work-pipeline refresh.
- Clearing them as one packet keeps the continuity controller moving without re-opening queue-state ownership.

## Validation

- `cd projects/agents && TMPDIR=/tmp uv run --with pytest pytest tests/test_research_jobs.py tests/test_scheduler.py tests/test_work_pipeline.py -q`
- `python scripts/generate_publication_deferred_family_queue.py`
- `python scripts/write_blocker_map.py --json`
- `python scripts/write_blocker_execution_plan.py --json`
- `python scripts/write_steady_state_status.py --json`

## Success Condition

- Scheduler and research-loop paths classify into `agent-execution-kernel-scheduler-and-research-loop`.
- `agent-execution-kernel-follow-on` advances to `self-improvement-and-proving`.
- The publication queue no longer reports these files as deferred family residue.

## Rollback

- Restore the listed scheduler/research files and this packet doc.
- Regenerate the publication queue, blocker map, blocker execution plan, and steady-state status.
