"""Constitutional constraint enforcement — code-level safety rails.

Loads CONSTITUTION.yaml and enforces its constraints programmatically.
This module is the central checkpoint for:
- DATA-001/002/003/004: Destructive data operations
- INFRA-003: Peak hours protection
- AUTO-003: Forbidden file modifications
- AUTO-002: Audit logging

Every check is logged regardless of outcome. Violations are hard-blocked
or escalated depending on the constraint's enforcement level.
"""

import fnmatch
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# CONSTITUTION.yaml path — read at startup, cached
_CONSTITUTION_PATH = Path(__file__).parent.parent.parent.parent.parent / "CONSTITUTION.yaml"
_constitution: dict[str, Any] | None = None


def _load_constitution() -> dict[str, Any]:
    """Load and cache CONSTITUTION.yaml. Returns empty dict on failure."""
    global _constitution
    if _constitution is not None:
        return _constitution
    try:
        _constitution = yaml.safe_load(_CONSTITUTION_PATH.read_text())
        logger.info("Loaded CONSTITUTION.yaml (version %s)", _constitution.get("version"))
    except Exception as e:
        logger.warning("Failed to load CONSTITUTION.yaml: %s — using defaults", e)
        _constitution = {}
    return _constitution


# --- Destructive operation thresholds ---
# Below these counts, the operation is allowed autonomously (with logging).
# Above these, escalation is required.
_AUTONOMOUS_DELETE_THRESHOLDS: dict[str, int] = {
    "activity": 500,          # Routine maintenance
    "events": 500,            # Routine maintenance
    "implicit_feedback": 500, # Ephemeral by design
    "llm_cache": 1000,        # Cache, fully disposable
}

# Collections that ALWAYS require approval for deletion
_PROTECTED_COLLECTIONS = {"personal_data", "conversations", "knowledge", "preferences"}

# Destructive operation keywords for pattern matching
_DESTRUCTIVE_PATTERNS = {
    "delete", "drop", "truncate", "purge", "remove", "destroy",
    "flushdb", "flushall", "del",
}


def check_destructive_operation(
    operation: str,
    target: str,
    count: int = 1,
    actor: str = "system",
) -> tuple[bool, str]:
    """Check whether a destructive operation is allowed.

    Args:
        operation: The operation type (delete, drop, truncate, purge, etc.)
        target: The target resource (collection name, table name, etc.)
        count: Number of items affected
        actor: Who is performing the operation

    Returns:
        (allowed, reason) — allowed=True means proceed, False means block/escalate
    """
    _load_constitution()
    op_lower = operation.lower()

    # Log every check
    _log_audit(
        operation_type=f"check:{op_lower}",
        target_resource=target,
        actor=actor,
        result="checking",
        constraint_checked=_identify_constraint(op_lower, target),
    )

    # DATA-002: Never drop collections/tables
    if op_lower in ("drop", "truncate"):
        reason = f"DATA-002: Cannot {op_lower} {target} — requires human approval"
        _log_audit(
            operation_type=op_lower,
            target_resource=target,
            actor=actor,
            result="blocked",
            constraint_checked="DATA-002",
        )
        return False, reason

    # DATA-004: Protected collections always require approval for deletion
    if target in _PROTECTED_COLLECTIONS and op_lower in ("delete", "purge"):
        reason = (
            f"DATA-004: Cannot {op_lower} from protected collection '{target}' "
            f"({count} items) — requires human approval"
        )
        _log_audit(
            operation_type=op_lower,
            target_resource=target,
            actor=actor,
            result="blocked",
            constraint_checked="DATA-004",
        )
        return False, reason

    # DATA-001: Deletion above threshold requires approval
    threshold = _AUTONOMOUS_DELETE_THRESHOLDS.get(target, 10)
    if op_lower in ("delete", "purge") and count > threshold:
        reason = (
            f"DATA-001: Deleting {count} items from '{target}' exceeds "
            f"autonomous threshold ({threshold}) — requires human approval"
        )
        _log_audit(
            operation_type=op_lower,
            target_resource=target,
            actor=actor,
            result="blocked",
            constraint_checked="DATA-001",
        )
        return False, reason

    # Allowed
    _log_audit(
        operation_type=op_lower,
        target_resource=target,
        actor=actor,
        result="allowed",
        constraint_checked=_identify_constraint(op_lower, target),
    )
    return True, "OK"


def is_peak_hours() -> bool:
    """Check if current time is during peak hours (8 AM — 10 PM local).

    INFRA-003: Never force-restart critical services during peak hours.
    """
    hour = datetime.now().hour
    return 8 <= hour < 22


def check_peak_hours_restart(service: str, actor: str = "system") -> tuple[bool, str]:
    """Check if a service restart is allowed right now.

    Returns (allowed, reason). During peak hours, returns False with
    a reason suitable for escalation/delay.
    """
    if not is_peak_hours():
        _log_audit(
            operation_type="restart",
            target_resource=service,
            actor=actor,
            result="allowed",
            constraint_checked="INFRA-003",
        )
        return True, "OK — off-peak hours"

    reason = (
        f"INFRA-003: Cannot restart '{service}' during peak hours "
        f"(8 AM — 10 PM). Current hour: {datetime.now().hour}. "
        f"Queue for off-peak or escalate for override."
    )
    _log_audit(
        operation_type="restart",
        target_resource=service,
        actor=actor,
        result="soft_blocked",
        constraint_checked="INFRA-003",
    )
    return False, reason


def check_forbidden_file(file_path: str, actor: str = "system") -> tuple[bool, str]:
    """Check if a file is in the forbidden modifications list.

    AUTO-003: Self-improvement proposals must not target forbidden files.

    Returns (allowed, reason).
    """
    const = _load_constitution()
    si_config = const.get("self_improvement", {})

    forbidden = si_config.get("forbidden_modifications", [
        "CONSTITUTION.yaml", ".env*", "**/secrets/**",
        "**/credentials/**", "/etc/**",
    ])
    allowed_globs = si_config.get("allowed_modifications", [
        "projects/**", "services/**", "scripts/**",
        "ansible/roles/**", "tests/**",
    ])

    # Check forbidden patterns first (takes priority)
    for pattern in forbidden:
        if fnmatch.fnmatch(file_path, pattern):
            reason = f"AUTO-003: File '{file_path}' matches forbidden pattern '{pattern}'"
            _log_audit(
                operation_type="file_modification",
                target_resource=file_path,
                actor=actor,
                result="blocked",
                constraint_checked="AUTO-003",
            )
            return False, reason

    # Check if file is within allowed globs
    in_allowed = any(fnmatch.fnmatch(file_path, g) for g in allowed_globs)
    if not in_allowed:
        reason = (
            f"AUTO-003: File '{file_path}' is outside allowed modification paths. "
            f"Allowed: {', '.join(allowed_globs)}"
        )
        _log_audit(
            operation_type="file_modification",
            target_resource=file_path,
            actor=actor,
            result="blocked",
            constraint_checked="AUTO-003",
        )
        return False, reason

    _log_audit(
        operation_type="file_modification",
        target_resource=file_path,
        actor=actor,
        result="allowed",
        constraint_checked="AUTO-003",
    )
    return True, "OK"


# --- Audit logging ---
# File-based audit log per CONSTITUTION.yaml AUTO-002 specification

_AUDIT_LOG_PATH = Path("/var/log/athanor/audit.log")
_audit_logger: logging.Logger | None = None


def _get_audit_logger() -> logging.Logger:
    """Get or create the file-based audit logger."""
    global _audit_logger
    if _audit_logger is not None:
        return _audit_logger

    _audit_logger = logging.getLogger("athanor.audit")
    _audit_logger.setLevel(logging.INFO)
    _audit_logger.propagate = False

    try:
        _AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(str(_AUDIT_LOG_PATH), encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s\t%(message)s", datefmt="%Y-%m-%dT%H:%M:%S%z"
        ))
        _audit_logger.addHandler(handler)
    except OSError:
        # Container may not have /var/log mounted — fall back to stderr
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "[AUDIT] %(asctime)s\t%(message)s", datefmt="%Y-%m-%dT%H:%M:%S%z"
        ))
        _audit_logger.addHandler(handler)

    return _audit_logger


def _log_audit(
    operation_type: str,
    target_resource: str,
    actor: str,
    result: str,
    constraint_checked: str = "",
    rollback_available: bool = False,
):
    """Write an audit log entry per CONSTITUTION.yaml spec."""
    audit = _get_audit_logger()
    entry = (
        f"op={operation_type}\t"
        f"target={target_resource}\t"
        f"actor={actor}\t"
        f"result={result}\t"
        f"constraint={constraint_checked}\t"
        f"rollback={rollback_available}"
    )
    audit.info(entry)


def _identify_constraint(operation: str, target: str) -> str:
    """Identify which constitutional constraint applies."""
    if operation in ("drop", "truncate"):
        return "DATA-002"
    if operation in ("delete", "purge") and target in _PROTECTED_COLLECTIONS:
        return "DATA-004"
    if operation in ("delete", "purge"):
        return "DATA-001"
    if operation == "restart":
        return "INFRA-003"
    if operation == "file_modification":
        return "AUTO-003"
    return ""


async def snapshot_point_ids(
    collection: str,
    point_ids: list[str],
) -> bool:
    """Snapshot point IDs to Redis before deletion (DATA-003 backup requirement).

    Stores IDs with 7-day TTL for recovery if needed.
    """
    if not point_ids:
        return True
    try:
        from .workspace import get_redis
        r = await get_redis()
        key = f"athanor:backup:deleted_ids:{collection}:{int(time.time())}"
        await r.set(key, json.dumps(point_ids), ex=7 * 86400)
        _log_audit(
            operation_type="backup_snapshot",
            target_resource=f"{collection}:{len(point_ids)} points",
            actor="system",
            result="saved",
            constraint_checked="DATA-003",
            rollback_available=True,
        )
        return True
    except Exception as e:
        logger.warning("Failed to snapshot point IDs for %s: %s", collection, e)
        return False
