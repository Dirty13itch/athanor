"""Compatibility helper that turns improvement proposals into canonical tasks.
Runs periodically to fetch proposals from the agent server and create durable tasks.
"""

from __future__ import annotations

from datetime import datetime
import uuid

import os

import requests

from _imports import AGENT_SERVER_URL


AGENT_SERVER = AGENT_SERVER_URL


def _read_secret(fpath: str) -> str:
    try:
        with open(fpath, encoding="utf-8") as handle:
            return handle.read().strip()
    except (OSError, IOError):
        return ""


def _agent_headers():
    """Read Agent Server auth token from secrets file or env."""
    key = os.environ.get("ATHANOR_AGENT_API_TOKEN") or _read_secret(
        "/home/shaun/.secrets/agent-server-api-key"
    )
    if key:
        return {"Authorization": f"Bearer {key}"}
    return {}


def get_proposals():
    """Fetch pending improvement proposals from Agent Server."""
    try:
        r = requests.get(
            f"{AGENT_SERVER}/v1/improvement/proposals",
            headers=_agent_headers(),
            timeout=10,
        )
        if r.status_code != 200:
            print(f"  Warning: Agent Server returned {r.status_code}: {r.text[:200]}")
            return []
        data = r.json()
        return data.get("proposals", [])
    except requests.RequestException as e:
        print(f"  Error fetching proposals: {e}")
        return []


def mark_proposal_processed(proposal_id: str):
    """Mark a proposal as processed on the Agent Server so it is not submitted twice."""
    try:
        r = requests.patch(
            f"{AGENT_SERVER}/v1/improvement/proposals/{proposal_id}",
            json={"status": "dispatched"},
            headers=_agent_headers(),
            timeout=10,
        )
        if r.status_code == 200:
            print(f"    Marked proposal {proposal_id} as dispatched")
        else:
            print(f"    Warning: Could not mark proposal {proposal_id}: {r.status_code}")
    except requests.RequestException as e:
        print(f"    Warning: Failed to mark proposal {proposal_id}: {e}")


def create_task_from_proposal(proposal):
    """Convert an improvement proposal to a canonical task-engine task."""
    proposal_id = proposal.get("id", "unknown")
    desc = proposal.get("description", "")
    cat = proposal.get("category", "unknown")
    agent = "research-agent" if cat in {"research", "analysis", "evaluation"} else "coding-agent"
    priority = "high" if cat in {"architecture", "safety", "security"} else "normal"
    task = {
        "agent": agent,
        "prompt": (
            "Review and execute this improvement proposal.\n"
            f"Title: {proposal.get('title', 'Improvement proposal')[:100]}\n"
            f"Description: {desc}\n"
            f"Category: {cat}\n"
            f"Proposal ID: {proposal_id}"
        ),
        "priority": priority,
        "metadata": {
            "source": "self_improve_loop",
            "proposal_id": proposal_id,
            "proposal_category": cat,
            "requires_approval": cat in {"architecture", "safety", "security"},
        },
        "actor": "self-improve-loop",
        "session_id": "self-improve-loop",
        "correlation_id": uuid.uuid4().hex,
        "reason": f"Submitted improvement proposal {proposal_id}",
    }
    try:
        r = requests.post(
            f"{AGENT_SERVER}/v1/tasks",
            json=task,
            headers=_agent_headers(),
            timeout=30,
        )
        if r.status_code == 200:
            result = r.json()
            task_id = (result.get("task") or {}).get("id")
            print(f"  Created task: {task_id} from proposal {proposal_id}")
            mark_proposal_processed(proposal_id)
            return result
        print(
            f"  Failed to create task from proposal {proposal_id}: {r.status_code} {r.text[:200]}"
        )
        return None
    except requests.RequestException as e:
        print(f"  Error creating task from proposal {proposal_id}: {e}")
        return None


def get_goals():
    """Fetch active goals to generate maintenance tasks."""
    try:
        r = requests.get(f"{AGENT_SERVER}/v1/goals", headers=_agent_headers(), timeout=10)
        if r.status_code == 200:
            return r.json().get("goals", [])
    except requests.RequestException as e:
        print(f"  Error fetching goals: {e}")
    return []


def run_self_improvement_cycle():
    """Main loop: proposals -> canonical tasks."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{timestamp}] Self-improvement cycle starting...")

    proposals = get_proposals()
    new_proposals = [p for p in proposals if p.get("status") in ("proposed", "pending")]

    if not new_proposals:
        total = len(proposals)
        print(f"  No new proposals (total returned: {total}, all already processed).")
        return

    print(f"  Found {len(new_proposals)} pending proposals (of {len(proposals)} total)")

    created = 0
    for proposal in new_proposals[:5]:
        result = create_task_from_proposal(proposal)
        if result:
            created += 1

    print(f"  Created {created} tasks from {len(new_proposals)} proposals")

    goals = get_goals()
    high_priority = [g for g in goals if g.get("priority") == "high" and g.get("active")]
    print(f"  {len(high_priority)} high-priority active goals")


if __name__ == "__main__":
    run_self_improvement_cycle()
