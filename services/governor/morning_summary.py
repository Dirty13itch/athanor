"""Morning Summary - reviews overnight work and sends digest."""
import subprocess
import json
import os
import glob
from datetime import datetime, timedelta

import os
NTFY_URL = os.environ.get("NTFY_URL", "http://192.168.1.203:8880")
NTFY_TOPIC = "athanor"

def notify(title, message, priority="default"):
    subprocess.run([
        "curl", "-sf", "-X", "POST", f"{NTFY_URL}/{NTFY_TOPIC}",
        "-H", f"Title: {title}",
        "-H", f"Priority: {priority}",
        "-H", "Tags: clipboard,athanor",
        "-d", message
    ], capture_output=True)

def get_overnight_commits():
    """Get git commits from last 12 hours across repos."""
    repos = ["/home/shaun/repos/athanor"]
    commits = []
    for repo in repos:
        result = subprocess.run(
            ["git", "-C", repo, "log", "--all", "--oneline", "--since=12 hours ago"],
            capture_output=True, text=True
        )
        if result.stdout.strip():
            commits.extend(result.stdout.strip().split("\n"))
    return commits

def get_agent_logs():
    """Summarize agent log files from overnight."""
    logs = glob.glob("/tmp/agent-logs/*.log")
    summaries = []
    for log in logs:
        try:
            with open(log) as f:
                content = f.read()
            lines = content.strip().split("\n")
            summaries.append(f"{os.path.basename(log)}: {len(lines)} lines")
        except:
            pass
    return summaries

def generate_summary():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    commits = get_overnight_commits()
    logs = get_agent_logs()
    
    summary = f"Morning Report {timestamp}\n"
    summary += f"Commits overnight: {len(commits)}\n"
    if commits:
        summary += "\n".join(commits[:10])
        if len(commits) > 10:
            summary += f"\n...and {len(commits)-10} more"
    summary += f"\nAgent logs: {len(logs)} files"
    
    notify("Morning Summary", summary, "default")
    print(summary)

if __name__ == "__main__":
    generate_summary()
