"""Intent Miner — discovers actionable intent from 13 sources.

Mines BUILD-MANIFEST, STATUS.md, project registry, active goals,
Qdrant signals, patterns, self-improvement proposals, diagnosis issues,
recent task outcomes, git TODOs, design docs, and operator chat.

Each source returns a list of RawIntent objects. The pipeline deduplicates
them against known intents before passing to plan generation.
"""

import json
import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
))))


@dataclass
class RawIntent:
    """A raw intent discovered from a source."""
    source: str  # Which of the sources
    text: str  # The actionable text
    metadata: dict = field(default_factory=dict)
    priority_hint: float = 0.5  # 0-1, higher = more urgent
    discovered_at: float = 0.0

    def __post_init__(self):
        if not self.discovered_at:
            self.discovered_at = time.time()


async def mine_all_sources() -> list[RawIntent]:
    """Mine all intent sources and return combined list."""
    intents: list[RawIntent] = []

    miners = [
        _mine_build_manifest,
        _mine_status,
        _mine_project_needs,
        _mine_active_goals,
        _mine_signals,
        _mine_patterns,
        _mine_self_improvement,
        _mine_diagnosis,
        _mine_task_outcomes,
        _mine_git_todos,
        _mine_design_docs,
        _mine_operator_intents,
    ]

    for miner in miners:
        try:
            results = await miner()
            intents.extend(results)
        except Exception as e:
            logger.warning("Intent miner %s failed: %s", miner.__name__, e)

    logger.info("Mined %d raw intents from %d sources", len(intents), len(miners))
    return intents


async def _mine_build_manifest() -> list[RawIntent]:
    """Parse BUILD-MANIFEST.md for unchecked items."""
    intents = []
    manifest_path = os.path.join(REPO_ROOT, "docs", "BUILD-MANIFEST.md")
    if not os.path.exists(manifest_path):
        return intents

    with open(manifest_path) as f:
        content = f.read()

    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("- [ ]"):
            text = stripped[5:].strip()
            if text:
                intents.append(RawIntent(
                    source="build_manifest",
                    text=text,
                    priority_hint=0.7,
                ))

    return intents


async def _mine_status() -> list[RawIntent]:
    """Parse STATUS.md for Next Actions section."""
    intents = []
    status_path = os.path.join(REPO_ROOT, "STATUS.md")
    if not os.path.exists(status_path):
        return intents

    with open(status_path) as f:
        content = f.read()

    in_next_actions = False
    for line in content.splitlines():
        if "next action" in line.lower() or "## next" in line.lower():
            in_next_actions = True
            continue
        if in_next_actions:
            if line.startswith("## "):
                break
            stripped = line.strip()
            if stripped.startswith("- ") or stripped.startswith("* "):
                text = stripped[2:].strip()
                if text and not text.startswith("[x]"):
                    intents.append(RawIntent(
                        source="status_md",
                        text=text,
                        priority_hint=0.8,
                    ))

    return intents


async def _mine_project_needs() -> list[RawIntent]:
    """Extract ProjectNeed entries from the project registry."""
    intents = []
    try:
        from .projects import get_project_registry
        registry = get_project_registry()
        for proj in registry.values():
            for need in proj.needs:
                intents.append(RawIntent(
                    source="project_needs",
                    text=f"[{proj.name}] {need.description}",
                    metadata={"project": proj.id, "agent": need.agent, "type": need.type},
                    priority_hint=0.6 if need.priority == "normal" else 0.8,
                ))
    except Exception as e:
        logger.debug("Project needs mining failed: %s", e)
    return intents


async def _mine_active_goals() -> list[RawIntent]:
    """Extract active goals with priority."""
    intents = []
    try:
        from .goals import list_goals
        goals = await list_goals(active_only=True)
        for goal in goals:
            intents.append(RawIntent(
                source="active_goals",
                text=goal.get("text", goal.get("description", goal.get("title", ""))),
                metadata={"goal_id": goal.get("id", "")},
                priority_hint=0.9 if goal.get("priority") == "high" else 0.6,
            ))
    except Exception as e:
        logger.debug("Goals mining failed: %s", e)
    return intents


async def _mine_signals() -> list[RawIntent]:
    """Query Qdrant signals collection for RSS-derived intelligence.

    Uses pagination and freshness decay: signals older than 7 days get
    halved relevance, older than 30 days are skipped entirely.
    """
    import time as _time

    intents = []
    try:
        from qdrant_client import QdrantClient
        from .config import settings

        client = QdrantClient(url=settings.qdrant_url)
        now = _time.time()
        seven_days = 7 * 86400
        thirty_days = 30 * 86400

        # Paginated scan — up to 100 signals
        offset = None
        total_scanned = 0
        while total_scanned < 100:
            results = client.scroll(
                collection_name="signals",
                limit=20,
                offset=offset,
                with_payload=True,
            )
            points = results[0] if results else []
            if not points:
                break

            offset = results[1]  # next page token
            total_scanned += len(points)

            for point in points:
                payload = point.payload or {}
                relevance = payload.get("relevance_score", 0)

                # Freshness decay
                crawled_at = payload.get("crawled_at", payload.get("timestamp", 0))
                if isinstance(crawled_at, str):
                    try:
                        from datetime import datetime
                        crawled_at = datetime.fromisoformat(crawled_at.replace("Z", "+00:00")).timestamp()
                    except (ValueError, TypeError):
                        crawled_at = 0

                age = now - (crawled_at if isinstance(crawled_at, (int, float)) else 0)
                if age > thirty_days:
                    continue  # Skip stale signals
                if age > seven_days:
                    relevance *= 0.5  # Halve relevance for older signals

                if relevance >= 0.6:
                    intents.append(RawIntent(
                        source="signals",
                        text=payload.get("title", "") + ": " + payload.get("summary", ""),
                        metadata={"signal_id": str(point.id), "relevance": relevance,
                                  "age_days": round(age / 86400, 1)},
                        priority_hint=min(relevance, 0.8),
                    ))

            if offset is None:
                break
    except Exception as e:
        logger.debug("Signals mining failed: %s", e)
    return intents


async def _mine_patterns() -> list[RawIntent]:
    """Read pattern detection recommendations from Redis."""
    intents = []
    try:
        from .workspace import get_redis
        r = await get_redis()
        report = await r.get("athanor:patterns:report")
        if report:
            text = report.decode() if isinstance(report, bytes) else report
            try:
                data = json.loads(text)
                for rec in data.get("recommendations", []):
                    intents.append(RawIntent(
                        source="patterns",
                        text=rec.get("description", ""),
                        metadata={"pattern_id": rec.get("id", "")},
                        priority_hint=0.5,
                    ))
            except json.JSONDecodeError:
                pass
    except Exception as e:
        logger.debug("Patterns mining failed: %s", e)
    return intents


async def _mine_self_improvement() -> list[RawIntent]:
    """Read self-improvement proposals from Redis."""
    intents = []
    try:
        from .workspace import get_redis
        r = await get_redis()
        raw = await r.lrange("athanor:improvement:proposals", 0, 10)
        for item in raw:
            text = item.decode() if isinstance(item, bytes) else item
            try:
                proposal = json.loads(text)
                intents.append(RawIntent(
                    source="self_improvement",
                    text=proposal.get("description", proposal.get("title", "")),
                    metadata={"proposal_id": proposal.get("id", "")},
                    priority_hint=0.4,
                ))
            except json.JSONDecodeError:
                pass
    except Exception as e:
        logger.debug("Self-improvement mining failed: %s", e)
    return intents


async def _mine_diagnosis() -> list[RawIntent]:
    """Read diagnosis issues from Redis."""
    intents = []
    try:
        from .workspace import get_redis
        r = await get_redis()
        raw = await r.lrange("athanor:diagnosis:issues", 0, 10)
        for item in raw:
            text = item.decode() if isinstance(item, bytes) else item
            try:
                issue = json.loads(text)
                intents.append(RawIntent(
                    source="diagnosis",
                    text=f"Fix: {issue.get('description', '')}",
                    metadata={"severity": issue.get("severity", "low")},
                    priority_hint=0.7 if issue.get("severity") == "high" else 0.5,
                ))
            except json.JSONDecodeError:
                pass
    except Exception as e:
        logger.debug("Diagnosis mining failed: %s", e)
    return intents


async def _mine_task_outcomes() -> list[RawIntent]:
    """Check recent task outcomes for retries and extensions."""
    intents = []
    try:
        from .workspace import get_redis
        r = await get_redis()
        raw = await r.lrange("athanor:pipeline:outcomes", 0, 20)
        for item in raw:
            text = item.decode() if isinstance(item, bytes) else item
            try:
                outcome = json.loads(text)
                if outcome.get("quality_score", 1.0) < 0.4 and not outcome.get("retried"):
                    intents.append(RawIntent(
                        source="task_outcomes",
                        text=f"Retry failed task: {outcome.get('prompt', '')[:200]}",
                        metadata={"original_task_id": outcome.get("task_id", "")},
                        priority_hint=0.6,
                    ))
            except json.JSONDecodeError:
                pass
    except Exception as e:
        logger.debug("Task outcomes mining failed: %s", e)
    return intents


async def _mine_git_todos() -> list[RawIntent]:
    """Scan recent git commits for TODO/FIXME/HACK comments."""
    intents = []
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-20", "--all"],
            capture_output=True, text=True, timeout=10,
            cwd=REPO_ROOT,
        )
        if result.returncode != 0:
            return intents

        # Grep for TODO/FIXME/HACK in recent diffs
        diff_result = subprocess.run(
            ["git", "diff", "HEAD~5..HEAD"],
            capture_output=True, text=True, timeout=10,
            cwd=REPO_ROOT,
        )
        if diff_result.returncode == 0:
            for line in diff_result.stdout.splitlines():
                if line.startswith("+") and not line.startswith("+++"):
                    for marker in ("TODO:", "FIXME:", "HACK:"):
                        if marker in line:
                            text = line[line.index(marker):].strip()
                            intents.append(RawIntent(
                                source="git_todos",
                                text=text,
                                priority_hint=0.4,
                            ))
    except Exception as e:
        logger.debug("Git TODO mining failed: %s", e)
    return intents


async def _mine_design_docs() -> list[RawIntent]:
    """Parse design docs for planned/unimplemented sections."""
    intents = []
    design_dir = os.path.join(REPO_ROOT, "docs", "design")
    if not os.path.isdir(design_dir):
        return intents

    planned_patterns = re.compile(
        r"(?:planned|future|todo|not yet|unimplemented|stub)",
        re.IGNORECASE,
    )

    for fname in os.listdir(design_dir):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(design_dir, fname)
        try:
            with open(fpath) as f:
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith("#") and planned_patterns.search(stripped):
                        intents.append(RawIntent(
                            source="design_docs",
                            text=f"[{fname}] {stripped.lstrip('#').strip()}",
                            metadata={"file": fname},
                            priority_hint=0.3,
                        ))
        except Exception:
            pass

    return intents


async def _mine_operator_intents() -> list[RawIntent]:
    """Read operator intents from Redis (captured from Command Center chat)."""
    intents = []
    try:
        from .workspace import get_redis
        r = await get_redis()
        raw = await r.lrange("athanor:intents:operator", 0, 20)
        for item in raw:
            text = item.decode() if isinstance(item, bytes) else item
            intents.append(RawIntent(
                source="operator_chat",
                text=text,
                priority_hint=0.9,  # Operator intents are highest priority
            ))
    except Exception as e:
        logger.debug("Operator intents mining failed: %s", e)
    return intents
