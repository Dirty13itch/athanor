"""Canonical status report helper.
Run manually or via cron to summarize current state from live control-plane surfaces.
"""

from __future__ import annotations

from datetime import datetime

import requests

from _imports import AGENT_SERVER_URL, DASHBOARD_URL


AGENT_SERVER = AGENT_SERVER_URL
DASHBOARD = DASHBOARD_URL


def generate_report():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    report = []
    report.append(f"=== ATHANOR STATUS REPORT - {now} ===\n")

    try:
        goals = requests.get(f"{AGENT_SERVER}/v1/goals", timeout=10).json().get("goals", [])
        active = [g for g in goals if g.get("active")]
        report.append(f"YOUR GOALS ({len(active)} active):")
        for g in sorted(
            active,
            key=lambda x: {"high": 0, "medium": 1, "normal": 2}.get(x.get("priority", "normal"), 3),
        ):
            pri = g.get("priority", "?")
            agent = g.get("agent", "global")
            text = g.get("text", "")[:85]
            report.append(f"  [{pri:6s}] ({agent:20s}) {text}")
    except Exception as e:
        report.append(f"  Goals: unavailable ({e})")

    try:
        stats = requests.get(f"{AGENT_SERVER}/v1/tasks/stats", timeout=10).json()
        report.append("\nTASK ENGINE:")
        report.append(
            "  "
            f"Pending: {stats.get('pending', 0)} | "
            f"Pending approval: {stats.get('pending_approval', 0)} | "
            f"Running: {stats.get('running', 0)} | "
            f"Completed: {stats.get('completed', 0)} | "
            f"Failed: {stats.get('failed', 0)} | "
            f"Cancelled: {stats.get('cancelled', 0)}"
        )
    except Exception as e:
        report.append(f"  Task engine: unavailable ({e})")

    try:
        proposals = requests.get(f"{AGENT_SERVER}/v1/improvement/proposals", timeout=10).json().get("proposals", [])
        pending = [p for p in proposals if p.get("status") == "proposed"]
        if pending:
            report.append(f"\nSYSTEM SELF-IMPROVEMENT ({len(pending)} pending proposals):")
            for p in pending[:5]:
                cat = p.get("category", "?")
                title = p.get("title", "")[:75]
                report.append(f"  [{cat:8s}] {title}")
    except Exception as e:
        report.append(f"  Proposals: unavailable ({e})")

    try:
        health = requests.get(f"{AGENT_SERVER}/health", timeout=10).json()
        agents = health.get("agents", [])
        report.append(f"\nAGENTS ({len(agents)} online): {', '.join(agents)}")
    except Exception as e:
        report.append(f"  Agents: unavailable ({e})")

    try:
        subs = requests.get(f"{DASHBOARD}/api/subscriptions/summary", timeout=10).json()
        providers = subs.get("provider_summaries", [])
        if providers:
            ready = [p for p in providers if p.get("direct_execution_ready")]
            handoff = [p for p in providers if p.get("governed_handoff_ready")]
            report.append(
                f"\nSUBSCRIPTIONS: {len(providers)} providers | {len(ready)} direct-ready | {len(handoff)} handoff-ready"
            )
    except Exception as e:
        report.append(f"  Subscriptions: unavailable ({e})")

    try:
        skills = requests.get(f"{AGENT_SERVER}/v1/skills", timeout=10).json()
        skill_list = skills.get("skills", skills) if isinstance(skills, dict) else skills
        if isinstance(skill_list, list):
            report.append(f"\nLEARNED SKILLS: {len(skill_list)}")
    except Exception:
        pass

    report.append(
        "\nSYSTEM HEALTH: Run 'bash scripts/drift-check.sh' for registry-backed drift verification and "
        "'python scripts/run_service_contract_tests.py' for the service contract bundle"
    )
    report.append(f"\n{'=' * 60}")
    report.append(f"Dashboard: {DASHBOARD_URL}")
    report.append(f"Subscriptions: {DASHBOARD_URL}/subscriptions")
    report.append(f"Agents: {DASHBOARD_URL}/agents")
    report.append(f"Governor: {DASHBOARD_URL}/governor")
    return "\n".join(report)


if __name__ == "__main__":
    print(generate_report())
