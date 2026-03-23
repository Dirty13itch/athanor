"""Self-Improvement Loop \u2014 connects Agent Server proposals to Governor dispatch.
Runs periodically to check for new improvement proposals and create tasks from them.
"""
import requests
import json
from datetime import datetime

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))

try:
    from cluster_config import get_url
    AGENT_SERVER = get_url("agent_server")
except Exception:
    AGENT_SERVER = os.environ.get("AGENT_SERVER_URL", "http://192.168.1.244:9000")

GOVERNOR = "http://localhost:8760"


def _read_secret(fpath: str) -> str:
    try:
        return open(fpath).read().strip()
    except (OSError, IOError):
        return ""


def _agent_headers():
    """Read Agent Server auth token from secrets file or env."""
    key = (
        os.environ.get("ATHANOR_AGENT_API_TOKEN")
        or _read_secret("/home/shaun/.secrets/agent-server-api-key")
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
        proposals = data.get("proposals", [])
        return proposals
    except requests.RequestException as e:
        print(f"  Error fetching proposals: {e}")
        return []


def mark_proposal_processed(proposal_id: str):
    """Mark a proposal as processed on the Agent Server so it is not re-queued."""
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
    """Convert an improvement proposal to a Governor task."""
    proposal_id = proposal.get("id", "unknown")
    desc = proposal.get("description", "")
    cat = proposal.get("category", "unknown")
    task = {
        "title": proposal.get("title", "Improvement proposal")[:100],
        "description": desc + "\nCategory: " + cat + "\nProposal ID: " + proposal_id,
        "repo": "athanor",
        "complexity": "medium" if cat == "prompt" else "low",
        "content_class": "cloud_safe",
    }
    try:
        r = requests.post(f"{GOVERNOR}/tasks", json=task, timeout=30)
        if r.status_code == 200:
            result = r.json()
            print(f"  Created task: {result.get('id')} from proposal {proposal_id}")
            mark_proposal_processed(proposal_id)
            return result
        else:
            print(f"  Failed to create task from proposal {proposal_id}: {r.status_code} {r.text[:200]}")
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
    """Main loop: proposals -> tasks -> dispatch."""
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
    for proposal in new_proposals[:5]:  # Max 5 per cycle
        result = create_task_from_proposal(proposal)
        if result:
            created += 1

    print(f"  Created {created} tasks from {len(new_proposals)} proposals")

    # Also check goals and create maintenance tasks
    goals = get_goals()
    high_priority = [g for g in goals if g.get("priority") == "high" and g.get("active")]
    print(f"  {len(high_priority)} high-priority active goals")


if __name__ == "__main__":
    run_self_improvement_cycle()
