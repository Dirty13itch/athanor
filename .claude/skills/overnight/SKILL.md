---
name: overnight
description: Manage overnight autonomous coding tasks
---

Manage the overnight coding pipeline:

- View next task: `cat ~/.claude/tasks/next-overnight.md`
- Edit next task: write new content to `~/.claude/tasks/next-overnight.md`
- View last run: `tail -100 /var/log/athanor/overnight-$(date +%Y%m%d).log`
- View cron: `cat /etc/cron.d/athanor-overnight`
- Manual trigger: `bash /home/shaun/bin/overnight-coding.sh`
- Check subscription status: `curl -s http://localhost:8065/status | python3 -m json.tool`

The overnight script runs at 2am via cron. It uses subscription auth (no API keys).