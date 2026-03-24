"""Status Report Generator — shows exactly what the system is doing and has done.
Run manually or via cron to see full system state at a glance.
"""
import requests
import json
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from cluster_config import AGENT_SERVER_URL, DASHBOARD_URL, GOVERNOR_URL, DEV_HOST
from datetime import datetime

AGENT_SERVER = AGENT_SERVER_URL
GOVERNOR = "http://localhost:8760"
DASHBOARD = "http://localhost:3001"

def generate_report():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    report = []
    report.append(f"=== ATHANOR STATUS REPORT - {now} ===\n")

    # 1. Goals — what YOU want the system working on
    try:
        goals = requests.get(f"{AGENT_SERVER}/v1/goals", timeout=10).json().get("goals", [])
        active = [g for g in goals if g.get("active")]
        report.append(f"YOUR GOALS ({len(active)} active):")
        for g in sorted(active, key=lambda x: {"high":0,"medium":1,"normal":2}.get(x.get("priority","normal"),3)):
            pri = g.get("priority", "?")
            agent = g.get("agent", "global")
            text = g.get("text", "")[:85]
            report.append(f"  [{pri:6s}] ({agent:20s}) {text}")
    except Exception as e:
        report.append(f"  Goals: unavailable ({e})")

    # 2. Governor task queue — what's queued across ALL projects
    try:
        stats = requests.get(f"{GOVERNOR}/stats", timeout=10).json()
        report.append(f"\nTASK QUEUE:")
        report.append(f"  Queued: {stats.get('queued',0)} | Running: {stats.get('running',0)} | Done: {stats.get('done',0)} | Failed: {stats.get('failed',0)}")
    except Exception as e:
        report.append(f"  Governor: unavailable ({e})")

    # 3. Self-improvement proposals (system-generated)
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

    # 4. Agent health
    try:
        health = requests.get(f"{AGENT_SERVER}/health", timeout=10).json()
        agents = health.get("agents", [])
        report.append(f"\nAGENTS ({len(agents)} online): {', '.join(agents)}")
    except Exception as e:
        report.append(f"  Agents: unavailable ({e})")

    # 5. Subscription burn
    try:
        subs = requests.get(f"{DASHBOARD}/api/subscriptions/summary", timeout=10).json()
        providers = subs.get("provider_summaries", [])
        if providers:
            ready = [p for p in providers if p.get("direct_execution_ready")]
            handoff = [p for p in providers if p.get("governed_handoff_ready")]
            report.append(f"\nSUBSCRIPTIONS: {len(providers)} providers | {len(ready)} direct-ready | {len(handoff)} handoff-ready")
    except Exception as e:
        report.append(f"  Subscriptions: unavailable ({e})")

    # 6. Skills learned
    try:
        skills = requests.get(f"{AGENT_SERVER}/v1/skills", timeout=10).json()
        skill_list = skills.get("skills", skills) if isinstance(skills, dict) else skills
        if isinstance(skill_list, list):
            report.append(f"\nLEARNED SKILLS: {len(skill_list)}")
    except:
        pass

    # 7. Drift check
    report.append(f"\nSYSTEM HEALTH: Run 'bash ~/repos/athanor/scripts/drift-check.sh' for full 37-check verification")

    report.append(f"\n{'='*60}")
    report.append(f"Dashboard: {DASHBOARD_URL}")
    report.append(f"Subscriptions: {DASHBOARD_URL}/subscriptions")
    report.append(f"Agents: {DASHBOARD_URL}/agents")
    report.append(f"Governor: {GOVERNOR_URL}/status")
    return "\n".join(report)

if __name__ == "__main__":
    print(generate_report())
