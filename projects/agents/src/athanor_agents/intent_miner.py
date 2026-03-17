"""Intent Miner — discovers actionable intent from 15 sources.

Mines BUILD-MANIFEST, STATUS.md, project registry, active goals,
Qdrant signals, patterns, self-improvement proposals, diagnosis issues,
recent task outcomes, git TODOs, design docs, operator chat,
content completeness, creative quality, and infrastructure drift.

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
        _mine_content_completeness,
        _mine_creative_quality,
        _mine_infrastructure_drift,
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


async def _mine_content_completeness() -> list[RawIntent]:
    """Scan EoBQ video inventory for queens missing I2V videos.

    Checks Redis athanor:eoq:video_inventory for each known queen.
    Queens missing default-stage videos get priority 0.6,
    queens missing other stages get 0.4.
    """
    intents = []
    try:
        from .workspace import get_redis
        r = await get_redis()

        # Get known queen IDs from Redis set or fall back to character list
        queen_ids = await r.smembers("athanor:eoq:queen_ids")
        if not queen_ids:
            # Fall back to keys in the creative tool's character dict
            queen_ids = {
                b"emilie-ekstrom", b"jordan-night", b"alanah-rae", b"nikki-benz",
                b"chloe-lamour", b"nicolette-shea", b"peta-jensen", b"sandee-westgate",
                b"marisol-yotta", b"trina-michaels", b"nikki-sexx", b"madison-ivy",
                b"amy-anderssen", b"puma-swede", b"ava-addams", b"brooklyn-chase",
                b"esperanza-gomez", b"savannah-bond", b"shyla-stylez", b"brianna-banks",
                b"clanddi-jinkcebo",
            }

        stages = ["defiant", "struggling", "conflicted", "yielding", "surrendered", "broken"]

        for qid_raw in queen_ids:
            qid = qid_raw.decode() if isinstance(qid_raw, bytes) else qid_raw

            for stage in stages:
                inv_key = f"athanor:eoq:video_inventory:{qid}:{stage}"
                exists = await r.exists(inv_key)
                if not exists:
                    priority = 0.6 if stage == "defiant" else 0.4
                    intents.append(RawIntent(
                        source="content_completeness",
                        text=f"Generate I2V video for queen '{qid}' at {stage} stage",
                        metadata={"queen_id": qid, "stage": stage, "project": "eoq"},
                        priority_hint=priority,
                    ))
    except Exception as e:
        logger.debug("Content completeness mining failed: %s", e)
    return intents


async def _mine_creative_quality() -> list[RawIntent]:
    """Scan video quality scores for low-quality or quick-preview videos.

    Reads Redis athanor:eoq:video_quality for entries with score < 0.5
    or quality level "quick" that could be upgraded to "production".
    """
    intents = []
    try:
        from .workspace import get_redis
        r = await get_redis()

        # Scan for all video quality entries
        cursor = b"0"
        while True:
            cursor, keys = await r.scan(cursor, match="athanor:eoq:video_quality:*", count=50)
            for key in keys:
                raw = await r.get(key)
                if not raw:
                    continue
                try:
                    data = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
                    score = data.get("score", 1.0)
                    quality_level = data.get("quality", "production")
                    queen_id = data.get("queen_id", "")
                    stage = data.get("stage", "")

                    if score < 0.5:
                        intents.append(RawIntent(
                            source="creative_quality",
                            text=f"Regenerate low-quality video for '{queen_id}' at {stage} (score={score:.2f})",
                            metadata={"queen_id": queen_id, "stage": stage, "score": score,
                                      "action": "regenerate", "project": "eoq"},
                            priority_hint=0.5,
                        ))
                    elif quality_level == "quick":
                        intents.append(RawIntent(
                            source="creative_quality",
                            text=f"Upgrade quick-preview video to production for '{queen_id}' at {stage}",
                            metadata={"queen_id": queen_id, "stage": stage,
                                      "action": "upgrade", "project": "eoq"},
                            priority_hint=0.3,
                        ))
                except json.JSONDecodeError:
                    pass

            if cursor == b"0":
                break
    except Exception as e:
        logger.debug("Creative quality mining failed: %s", e)
    return intents


async def _mine_infrastructure_drift() -> list[RawIntent]:
    """Compare SERVICES.md documented ports/containers against live docker state.

    Runs docker ps on accessible nodes and diffs against SERVICES.md.
    Emits intents for discrepancies found.
    """
    intents = []
    services_path = os.path.join(REPO_ROOT, "docs", "SERVICES.md")
    if not os.path.exists(services_path):
        return intents

    try:
        with open(services_path) as f:
            services_content = f.read()

        # Extract documented ports from SERVICES.md (format: :PORT or port PORT)
        documented_ports = set()
        for match in re.findall(r":(\d{4,5})", services_content):
            documented_ports.add(int(match))

        # Check live state via docker ps on local node
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Ports}}\t{{.Status}}"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return intents

        live_ports = set()
        live_containers = set()
        for line in result.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                live_containers.add(parts[0])
                for port_match in re.findall(r":(\d{4,5})->", parts[1]):
                    live_ports.add(int(port_match))

        # Find documented ports not exposed by any container
        missing = documented_ports - live_ports
        # Filter to only meaningful ports (ignore ephemeral)
        meaningful_missing = {p for p in missing if 1000 <= p <= 65000}

        if meaningful_missing:
            intents.append(RawIntent(
                source="infrastructure_drift",
                text=f"SERVICES.md documents ports {sorted(meaningful_missing)} but no containers expose them on this node",
                metadata={"missing_ports": sorted(meaningful_missing), "node": "dev"},
                priority_hint=0.4,
            ))
    except Exception as e:
        logger.debug("Infrastructure drift mining failed: %s", e)
    return intents
