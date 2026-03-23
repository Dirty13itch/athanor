"""Self-Improvement Loop — connects Agent Server proposals to Governor dispatch.
Runs periodically to check for new improvement proposals and create tasks from them.
"""
import requests
import json
from datetime import datetime

import os
AGENT_SERVER = os.environ.get("AGENT_SERVER_URL", "http://192.168.1.244:9000")
GOVERNOR = "http://localhost:8760"


def _agent_headers():
    """Read Agent Server auth token from secrets file."""
    try:
        key = open("/home/shaun/.secrets/agent-server-api-key").read().strip()
        return {"Authorization": f"Bearer {key}"}
    except Exception:
        return {}


def get_proposals():
    """Fetch pending improvement proposals from Agent Server."""
    r = requests.get(f"{AGENT_SERVER}/v1/improvement/proposals", headers=_agent_headers(), timeout=10)
    if r.status_code == 200:
        data = r.json()
        return data.get("proposals", [])
    return []

def create_task_from_proposal(proposal):
    """Convert an improvement proposal to a Governor task."""
    task = {
        "title": proposal.get("title", "Improvement proposal")[:100],
        "description": proposal.get("description", "") + "\n\nCategory: " + proposal.get("category", "unknown") + "\nProposal ID: " + proposal.get("id", "unknown"),
        "repo": "athanor",
        "complexity": "medium" if proposal.get("category") == "prompt" else "low",
        "content_class": "cloud_safe"
    }
    r = requests.post(f"{GOVERNOR}/tasks", json=task, timeout=30)
    if r.status_code == 200:
        return r.json()
    return None

def get_goals():
    """Fetch active goals to generate maintenance tasks."""
    r = requests.get(f"{AGENT_SERVER}/v1/goals", headers=_agent_headers(), timeout=10)
    if r.status_code == 200:
        return r.json().get("goals", [])
    return []

def run_self_improvement_cycle():
    """Main loop: proposals -> tasks -> dispatch."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{timestamp}] Self-improvement cycle starting...")

    proposals = get_proposals()
    new_proposals = [p for p in proposals if p.get("status") == "proposed"]

    if not new_proposals:
        print(f"  No new proposals.")
        return

    print(f"  Found {len(new_proposals)} pending proposals")

    created = 0
    for proposal in new_proposals[:5]:  # Max 5 per cycle
        result = create_task_from_proposal(proposal)
        if result:
            print(f"  Created task: {result.get('id')} from proposal {proposal.get('id')}")
            created += 1

    print(f"  Created {created} tasks from proposals")

    # Also check goals and create maintenance tasks
    goals = get_goals()
    high_priority = [g for g in goals if g.get("priority") == "high" and g.get("active")]
    print(f"  {len(high_priority)} high-priority active goals")

if __name__ == "__main__":
    run_self_improvement_cycle()
