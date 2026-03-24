"""Policy router: classifies tasks into policy classes before model/CLI selection.

Rule-based classifier — no LLM call needed. Every task gets a policy class that
determines whether it can touch cloud providers or must stay local. This runs
upstream of the subscription lease system in subscriptions.py.

Policy classes:
    reviewable         — Cloud CLI review is acceptable (coding, research, media)
    refusal_sensitive  — Content that cloud providers may refuse (stash, creative)
    sovereign_only     — Personal/home data that must never leave the LAN
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Policy class definitions
# ---------------------------------------------------------------------------

POLICY_CLASSES: dict[str, dict[str, Any]] = {
    "reviewable": {
        "description": "Cloud CLI review OK — code, research, media tasks",
        "cloud_allowed": True,
        "default_agents": ["coding-agent", "research-agent", "media-agent"],
    },
    "refusal_sensitive": {
        "description": "Content cloud providers may refuse — local only",
        "cloud_allowed": False,
        "default_agents": ["stash-agent", "creative-agent"],
    },
    "sovereign_only": {
        "description": "Personal/home data — never leaves the LAN",
        "cloud_allowed": False,
        "default_agents": [
            "home-agent",
            "knowledge-agent",
            "data-curator",
            "general-assistant",
        ],
    },
}

# Reverse lookup: agent name -> default policy class
_AGENT_POLICY_MAP: dict[str, str] = {}
for _cls_name, _cls_meta in POLICY_CLASSES.items():
    for _agent in _cls_meta["default_agents"]:
        _AGENT_POLICY_MAP[_agent] = _cls_name

# ---------------------------------------------------------------------------
# Keyword patterns for sensitivity escalation
# ---------------------------------------------------------------------------

_SOVEREIGN_KEYWORDS: re.Pattern[str] = re.compile(
    r"\b(personal|home\s+assistant|home\s+automation|private\s+data|"
    r"my\s+house|my\s+home|location|address|calendar|contacts)\b",
    re.IGNORECASE,
)

_REFUSAL_KEYWORDS: re.Pattern[str] = re.compile(
    r"\b(nsfw|adult|stash|porn|explicit|xxx|erotic)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_policy(
    agent: str,
    prompt: str = "",
    metadata: dict[str, Any] | None = None,
) -> str:
    """Classify a task into a policy class.

    Resolution order:
        1. Explicit ``policy_override`` in metadata
        2. Keyword scan on the prompt text
        3. Agent default from POLICY_CLASSES
        4. Fallback to ``sovereign_only`` (safest default)
    """
    meta = metadata or {}

    # 1. Explicit override
    override = meta.get("policy_override")
    if override and override in POLICY_CLASSES:
        return str(override)

    # 2. Keyword escalation (prompt-based)
    if prompt:
        if _REFUSAL_KEYWORDS.search(prompt):
            return "refusal_sensitive"
        if _SOVEREIGN_KEYWORDS.search(prompt):
            return "sovereign_only"

    # 3. Agent default
    if agent in _AGENT_POLICY_MAP:
        return _AGENT_POLICY_MAP[agent]

    # 4. Safe fallback
    return "sovereign_only"


def get_execution_lane(policy_class: str, interactive: bool = False) -> str:
    """Return the execution lane for a given policy class.

    Returns one of:
        CLI_MANAGED          — interactive reviewable task, cloud CLI drives
        LOCAL_WITH_CLI_REVIEW — batch reviewable task, local runs, CLI reviews
        LOCAL_ONLY           — sovereign or refusal-sensitive, stays on LAN
    """
    if policy_class == "reviewable":
        if interactive:
            return "CLI_MANAGED"
        return "LOCAL_WITH_CLI_REVIEW"

    # sovereign_only and refusal_sensitive both stay local
    return "LOCAL_ONLY"


def get_delegation_pattern(
    policy_class: str,
    task_type: str = "general",
) -> str:
    """Map a policy class and task type to a delegation pattern string.

    Returns one of:
        local_only          — must execute entirely on local infrastructure
        local_with_cli_review — local execution with cloud CLI reviewing output
        cli_execute         — cloud CLI drives execution directly
        cli_consensus       — multiple CLIs cross-check for high-stakes tasks
    """
    if policy_class in ("sovereign_only", "refusal_sensitive"):
        return "local_only"

    # reviewable tasks — delegation depends on task type
    _TASK_PATTERNS: dict[str, str] = {
        "architecture": "cli_consensus",
        "design": "cli_consensus",
        "review": "cli_execute",
        "implementation": "local_with_cli_review",
        "research": "cli_execute",
        "audit": "cli_execute",
        "bulk_transform": "local_with_cli_review",
        "general": "local_with_cli_review",
    }

    return _TASK_PATTERNS.get(task_type, "local_with_cli_review")


def is_cloud_allowed(policy_class: str) -> bool:
    """Quick check: can this policy class use cloud providers?"""
    cls_meta = POLICY_CLASSES.get(policy_class)
    if cls_meta is None:
        return False
    return bool(cls_meta.get("cloud_allowed", False))
