"""Athanor Watchdog runtime guard.

Standalone FastAPI service that polls cluster services, applies a
3-consecutive-failures threshold, and can run bounded Band A remediation
(container restart via SSH) when the runtime mutation gate is explicitly open.

The guard is intentionally fail-closed:
- monitoring stays live even while mutation authority is closed
- runtime mutation requires an explicit operator envelope
- runtime mutation also requires the packet/env gate to be open
- protected services remain page-only even for manual restart requests

Runs on FOUNDRY:9301 with ``network_mode: host``.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import PlainTextResponse

from catalog import SERVICES, SERVICES_BY_ID, ServiceCheck
from circuit import CircuitBreaker
from remediation import CheckResult, http_check, page_ntfy, restart_container, ssh_check, tcp_check

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("athanor.watchdog")

VERSION = "0.2.0"
SERVICE_NAME = "watchdog-runtime-guard"
MUTATION_ALLOWED_PACKET_STATUSES = {"executed"}
PRIVILEGE_CLASSES = {"read-only", "operator", "admin", "destructive-admin"}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _body_dict(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    return dict(payload) if isinstance(payload, Mapping) else {}


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _as_str(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


PORT = int(os.environ.get("WATCHDOG_PORT", "9301"))
TICK_SECONDS = int(os.environ.get("WATCHDOG_TICK_SECONDS", "15"))
INITIAL_PAUSED = _env_bool("WATCHDOG_INITIAL_PAUSED", True)
FAILURE_THRESHOLD = int(os.environ.get("WATCHDOG_FAILURE_THRESHOLD", "3"))
MUTATIONS_ENABLED = _env_bool("WATCHDOG_MUTATIONS_ENABLED", False)
RUNTIME_PACKET_ID = (
    os.environ.get("WATCHDOG_RUNTIME_PACKET_ID", "foundry-watchdog-runtime-guard-rollout-packet").strip()
    or "foundry-watchdog-runtime-guard-rollout-packet"
)
RUNTIME_PACKET_STATUS = (
    os.environ.get("WATCHDOG_RUNTIME_PACKET_STATUS", "ready_for_approval").strip()
    or "ready_for_approval"
)
AUDIT_LOG_PATH = Path(
    os.environ.get("WATCHDOG_AUDIT_LOG", "/var/log/athanor/watchdog-operator-audit.log").strip()
    or "/var/log/athanor/watchdog-operator-audit.log"
)


@dataclass
class ServiceState:
    status: str = "UNKNOWN"  # UNKNOWN | OK | CRIT
    last_check: float = 0.0
    last_latency_ms: int = 0
    last_error: str = ""
    consecutive_failures: int = 0
    last_remediation_at: float = 0.0
    paged_this_outage: bool = False
    circuit_open_paged: bool = False
    total_checks: int = 0
    total_failures: int = 0
    total_remediations: int = 0


@dataclass(frozen=True, slots=True)
class OperatorActionRequest:
    actor: str
    session_id: str
    correlation_id: str
    reason: str = ""
    dry_run: bool = False
    protected_mode: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


state: dict[str, ServiceState] = {svc.service_id: ServiceState() for svc in SERVICES}
cb = CircuitBreaker()
PAUSED = INITIAL_PAUSED


def build_operator_action(
    payload: Mapping[str, Any] | None,
    *,
    default_actor: str = "operator",
    default_reason: str = "",
) -> OperatorActionRequest:
    body = _body_dict(payload)
    return OperatorActionRequest(
        actor=_as_str(body.get("actor")) or default_actor,
        session_id=_as_str(body.get("session_id")) or "",
        correlation_id=_as_str(body.get("correlation_id")) or uuid.uuid4().hex,
        reason=_as_str(body.get("reason")) or default_reason,
        dry_run=_as_bool(body.get("dry_run")),
        protected_mode=_as_bool(body.get("protected_mode")),
    )


def validate_operator_action(action: OperatorActionRequest, *, action_class: str) -> None:
    if action_class not in PRIVILEGE_CLASSES:
        raise ValueError(f"Unsupported action class '{action_class}'")

    missing = [
        field
        for field, value in (
            ("actor", action.actor),
            ("session_id", action.session_id),
            ("correlation_id", action.correlation_id),
        )
        if not value
    ]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Operator action envelope missing required fields: {', '.join(missing)}",
        )

    if action_class in {"admin", "destructive-admin"} and not action.reason:
        raise HTTPException(
            status_code=400,
            detail="reason is required for admin and destructive-admin actions",
        )

    if action_class == "destructive-admin" and not action.protected_mode:
        raise HTTPException(
            status_code=400,
            detail="protected_mode=true is required for destructive-admin actions",
        )


def require_operator_action(
    payload: Mapping[str, Any] | None,
    *,
    action_class: str,
    default_actor: str = "operator",
    default_reason: str = "",
) -> OperatorActionRequest:
    action = build_operator_action(
        payload,
        default_actor=default_actor,
        default_reason=default_reason,
    )
    validate_operator_action(action, action_class=action_class)
    return action


def mutation_gate_blockers() -> list[str]:
    blockers: list[str] = []
    if not MUTATIONS_ENABLED:
        blockers.append("WATCHDOG_MUTATIONS_ENABLED=false")
    if RUNTIME_PACKET_STATUS not in MUTATION_ALLOWED_PACKET_STATUSES:
        blockers.append(
            f"runtime packet {RUNTIME_PACKET_ID} status is {RUNTIME_PACKET_STATUS}, requires executed"
        )
    return blockers


def mutation_gate_open() -> bool:
    return not mutation_gate_blockers()


def auto_remediation_enabled() -> bool:
    return mutation_gate_open() and not PAUSED


def auto_remediation_blockers() -> list[str]:
    blockers = list(mutation_gate_blockers())
    if PAUSED:
        blockers.append("watchdog is paused")
    return blockers


def control_mode() -> str:
    if PAUSED and not mutation_gate_open():
        return "paused_guarded"
    if PAUSED:
        return "paused"
    if not mutation_gate_open():
        return "guarded"
    return "active"


def service_manual_restart_reason(svc: ServiceCheck) -> str:
    if not mutation_gate_open():
        return "; ".join(mutation_gate_blockers())
    if not svc.manual_restart_allowed:
        return "manual restart is intentionally blocked for this protected service"
    return ""


def service_auto_remediation_reason(svc: ServiceCheck) -> str:
    if not svc.auto_remediate:
        return "service is page-only and excluded from automatic remediation"
    blockers = auto_remediation_blockers()
    if blockers:
        return "; ".join(blockers)
    return ""


def global_allowed_actions() -> dict[str, dict[str, Any]]:
    mutation_blockers = mutation_gate_blockers()
    return {
        "pause": {
            "allowed": True,
            "action_class": "admin",
            "blocked_by": [],
        },
        "resume": {
            "allowed": mutation_gate_open(),
            "action_class": "destructive-admin",
            "blocked_by": mutation_blockers,
        },
        "manual_restart": {
            "allowed": mutation_gate_open(),
            "action_class": "destructive-admin",
            "blocked_by": mutation_blockers,
        },
    }


def control_plane_snapshot() -> dict[str, Any]:
    return {
        "mode": control_mode(),
        "paused": PAUSED,
        "mutations_enabled": MUTATIONS_ENABLED,
        "mutation_gate_open": mutation_gate_open(),
        "auto_remediation_enabled": auto_remediation_enabled(),
        "runtime_packet_id": RUNTIME_PACKET_ID,
        "runtime_packet_status": RUNTIME_PACKET_STATUS,
        "mutation_gate_blockers": mutation_gate_blockers(),
        "auto_remediation_blockers": auto_remediation_blockers(),
        "allowed_actions": global_allowed_actions(),
    }


def _write_audit_event(
    *,
    route: str,
    action_class: str,
    decision: str,
    status_code: int,
    action: OperatorActionRequest,
    detail: str,
    target: str,
    metadata: Mapping[str, Any] | None = None,
) -> None:
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": SERVICE_NAME,
        "route": route,
        "action_class": action_class,
        "decision": decision,
        "status_code": status_code,
        "actor": action.actor,
        "session_id": action.session_id,
        "correlation_id": action.correlation_id,
        "reason": action.reason,
        "dry_run": action.dry_run,
        "protected_mode": action.protected_mode,
        "target": target,
        "detail": detail,
        "metadata": dict(metadata or {}),
    }
    try:
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
    except Exception as exc:
        logger.warning("watchdog audit log write failed: %s", exc)


async def emit_audit_event(
    *,
    route: str,
    action_class: str,
    decision: str,
    status_code: int,
    action: OperatorActionRequest,
    detail: str,
    target: str,
    metadata: Mapping[str, Any] | None = None,
) -> None:
    _write_audit_event(
        route=route,
        action_class=action_class,
        decision=decision,
        status_code=status_code,
        action=action,
        detail=detail,
        target=target,
        metadata=metadata,
    )


async def probe(svc: ServiceCheck) -> CheckResult:
    if svc.url.startswith("tcp://"):
        return await tcp_check(svc.url)
    if svc.url.startswith("ssh://"):
        return await ssh_check(svc.url)
    return await http_check(
        svc.url,
        accept_codes=svc.accept_codes,
        body_must_contain=svc.body_contains,
    )


async def tick() -> None:
    now = time.time()
    for svc in SERVICES:
        st = state[svc.service_id]
        if now - st.last_check < svc.frequency_seconds:
            continue

        result = await probe(svc)
        st.last_check = now
        st.last_latency_ms = result.latency_ms
        st.total_checks += 1

        if result.ok:
            if st.consecutive_failures >= FAILURE_THRESHOLD:
                cb.reset(svc.service_id)
                await page_ntfy(
                    title=f"RECOVERED: {svc.service_id}",
                    message=f"Service back up after {st.consecutive_failures} failed checks.",
                    priority="default",
                    tags="white_check_mark",
                )
            st.consecutive_failures = 0
            st.status = "OK"
            st.paged_this_outage = False
            st.circuit_open_paged = False
            st.last_error = ""
            continue

        st.consecutive_failures += 1
        st.total_failures += 1
        st.status = "CRIT"
        st.last_error = result.msg

        if st.consecutive_failures < FAILURE_THRESHOLD:
            continue

        if not auto_remediation_enabled():
            if not st.paged_this_outage:
                guard_reason = "; ".join(auto_remediation_blockers())
                await page_ntfy(
                    title=f"GUARDED: {svc.service_id} unhealthy",
                    message=f"{result.msg} ({guard_reason}; manual action required)",
                    priority="high",
                    tags="warning",
                )
                st.paged_this_outage = True
            continue

        if not svc.auto_remediate:
            if not st.paged_this_outage:
                await page_ntfy(
                    title=f"P0 DOWN: {svc.service_id}",
                    message=f"{result.msg} (no auto-restart configured for this service)",
                    priority="urgent",
                    tags="rotating_light,no_entry",
                )
                st.paged_this_outage = True
            continue

        if not cb.can_attempt(svc.service_id, max_per_hour=svc.max_restarts_per_hour):
            if not st.circuit_open_paged:
                await page_ntfy(
                    title=f"CIRCUIT OPEN: {svc.service_id}",
                    message=(
                        f"Auto-remediation exhausted ({svc.max_restarts_per_hour}/hr). "
                        f"Last error: {result.msg}. Manual investigation required."
                    ),
                    priority="urgent",
                    tags="rotating_light",
                )
                st.circuit_open_paged = True
            continue

        cb.record_attempt(svc.service_id)
        st.last_remediation_at = now
        st.total_remediations += 1
        rem = await restart_container(svc.node, svc.container)

        if rem.success:
            await page_ntfy(
                title=f"AUTO-RESTART: {svc.service_id}",
                message=(
                    f"Restarted {svc.container} on {svc.node} "
                    f"(took {rem.duration_ms}ms). Will verify next cycle."
                ),
                priority="default",
                tags="arrows_counterclockwise",
            )
        else:
            await page_ntfy(
                title=f"RESTART FAILED: {svc.service_id}",
                message=f"docker restart failed: {rem.error}",
                priority="urgent",
                tags="rotating_light",
            )


async def main_loop() -> None:
    logger.info(
        "Watchdog main loop starting (tick=%ds, mode=%s, packet=%s/%s)",
        TICK_SECONDS,
        control_mode(),
        RUNTIME_PACKET_ID,
        RUNTIME_PACKET_STATUS,
    )
    while True:
        try:
            await tick()
        except Exception:
            logger.exception("watchdog tick error")
        await asyncio.sleep(TICK_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(main_loop())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(
    title="Athanor Watchdog Runtime Guard",
    description="Health monitoring with fail-closed bounded remediation.",
    version=VERSION,
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "watchdog",
        "version": VERSION,
        "paused": PAUSED,
        "mutations_enabled": MUTATIONS_ENABLED,
        "mutation_gate_open": mutation_gate_open(),
        "services_monitored": len(SERVICES),
        "tick_seconds": TICK_SECONDS,
        "control_plane": control_plane_snapshot(),
    }


@app.get("/status")
async def status() -> dict[str, Any]:
    out: dict[str, Any] = {
        "summary": {
            "total": len(SERVICES),
            "ok": sum(1 for service_id in state if state[service_id].status == "OK"),
            "crit": sum(1 for service_id in state if state[service_id].status == "CRIT"),
            "unknown": sum(1 for service_id in state if state[service_id].status == "UNKNOWN"),
        },
        "tick_seconds": TICK_SECONDS,
        "control_plane": control_plane_snapshot(),
        "services": {},
        "circuit_breaker": cb.state_snapshot(),
    }
    for svc in SERVICES:
        st = state[svc.service_id]
        manual_reason = service_manual_restart_reason(svc)
        auto_reason = service_auto_remediation_reason(svc)
        out["services"][svc.service_id] = {
            "node": svc.node,
            "container": svc.container,
            "url": svc.url,
            "p0": svc.p0,
            "auto_remediate": svc.auto_remediate,
            "manual_restart_allowed": svc.manual_restart_allowed,
            "max_restarts_per_hour": svc.max_restarts_per_hour,
            "frequency_seconds": svc.frequency_seconds,
            "status": st.status,
            "last_check": st.last_check,
            "last_check_age_seconds": int(time.time() - st.last_check) if st.last_check else None,
            "last_latency_ms": st.last_latency_ms,
            "last_error": st.last_error,
            "consecutive_failures": st.consecutive_failures,
            "total_checks": st.total_checks,
            "total_failures": st.total_failures,
            "total_remediations": st.total_remediations,
            "last_remediation_at": st.last_remediation_at,
            "allowed_actions": {
                "manual_restart": {
                    "allowed": not manual_reason,
                    "action_class": "destructive-admin",
                    "blocked_by": [manual_reason] if manual_reason else [],
                },
                "auto_remediation": {
                    "allowed": not auto_reason,
                    "blocked_by": [auto_reason] if auto_reason else [],
                },
            },
        }
    return out


@app.post("/pause")
async def pause(payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
    global PAUSED

    action = require_operator_action(
        payload,
        action_class="admin",
        default_reason="Pause watchdog auto-remediation",
    )
    if action.dry_run:
        await emit_audit_event(
            route="/pause",
            action_class="admin",
            decision="dry-run",
            status_code=200,
            action=action,
            detail="Dry-run pause accepted; auto-remediation would remain paused.",
            target="global",
            metadata={"current_mode": control_mode()},
        )
        return {
            "paused": True,
            "dry_run": True,
            "control_plane": control_plane_snapshot(),
        }

    PAUSED = True
    await page_ntfy(
        title="WATCHDOG PAUSED",
        message="Auto-remediation disabled by operator. Monitoring continues.",
        priority="high",
        tags="pause_button",
    )
    await emit_audit_event(
        route="/pause",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail="Auto-remediation paused by operator request.",
        target="global",
        metadata={"current_mode": control_mode()},
    )
    return {
        "paused": True,
        "control_plane": control_plane_snapshot(),
    }


@app.post("/resume")
async def resume(payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
    global PAUSED

    action = require_operator_action(
        payload,
        action_class="destructive-admin",
        default_reason="Resume watchdog auto-remediation",
    )
    blockers = mutation_gate_blockers()
    if blockers:
        detail = "mutation gate closed: " + "; ".join(blockers)
        await emit_audit_event(
            route="/resume",
            action_class="destructive-admin",
            decision="denied",
            status_code=409,
            action=action,
            detail=detail,
            target="global",
            metadata={"runtime_packet_id": RUNTIME_PACKET_ID, "runtime_packet_status": RUNTIME_PACKET_STATUS},
        )
        raise HTTPException(status_code=409, detail=detail)

    if action.dry_run:
        await emit_audit_event(
            route="/resume",
            action_class="destructive-admin",
            decision="dry-run",
            status_code=200,
            action=action,
            detail="Dry-run resume accepted; auto-remediation would be enabled.",
            target="global",
            metadata={"current_mode": control_mode()},
        )
        return {
            "paused": False,
            "dry_run": True,
            "control_plane": control_plane_snapshot(),
        }

    PAUSED = False
    await page_ntfy(
        title="WATCHDOG RESUMED",
        message="Auto-remediation re-enabled by operator.",
        priority="default",
        tags="play_pause",
    )
    await emit_audit_event(
        route="/resume",
        action_class="destructive-admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail="Auto-remediation resumed by operator request.",
        target="global",
        metadata={"current_mode": control_mode()},
    )
    return {
        "paused": False,
        "control_plane": control_plane_snapshot(),
    }


@app.post("/service/{service_id}/restart")
async def manual_restart(
    service_id: str,
    payload: dict[str, Any] | None = Body(default=None),
) -> dict[str, Any]:
    action = require_operator_action(
        payload,
        action_class="destructive-admin",
        default_reason=f"Manual watchdog restart for {service_id}",
    )
    svc = SERVICES_BY_ID.get(service_id)
    if not svc:
        await emit_audit_event(
            route="/service/{service_id}/restart",
            action_class="destructive-admin",
            decision="denied",
            status_code=404,
            action=action,
            detail=f"unknown service_id: {service_id}",
            target=service_id,
            metadata={"service_id": service_id},
        )
        raise HTTPException(status_code=404, detail=f"unknown service_id: {service_id}")

    manual_reason = service_manual_restart_reason(svc)
    if manual_reason:
        await emit_audit_event(
            route="/service/{service_id}/restart",
            action_class="destructive-admin",
            decision="denied",
            status_code=409,
            action=action,
            detail=manual_reason,
            target=service_id,
            metadata={"node": svc.node, "container": svc.container},
        )
        raise HTTPException(status_code=409, detail=manual_reason)

    if action.dry_run:
        await emit_audit_event(
            route="/service/{service_id}/restart",
            action_class="destructive-admin",
            decision="dry-run",
            status_code=200,
            action=action,
            detail=f"Dry-run manual restart accepted for {svc.container} on {svc.node}.",
            target=service_id,
            metadata={"node": svc.node, "container": svc.container},
        )
        return {
            "service_id": service_id,
            "dry_run": True,
            "success": True,
            "planned_action": f"docker restart {svc.container} on {svc.node}",
            "control_plane": control_plane_snapshot(),
        }

    rem = await restart_container(svc.node, svc.container)
    decision = "accepted" if rem.success else "failed"
    status_code = 200 if rem.success else 502
    detail = (
        f"Operator-triggered restart of {svc.container} on {svc.node}"
        if rem.success
        else f"Manual restart failed: {rem.error}"
    )
    await emit_audit_event(
        route="/service/{service_id}/restart",
        action_class="destructive-admin",
        decision=decision,
        status_code=status_code,
        action=action,
        detail=detail,
        target=service_id,
        metadata={"node": svc.node, "container": svc.container, "duration_ms": rem.duration_ms},
    )
    if rem.success:
        await page_ntfy(
            title=f"MANUAL-RESTART: {service_id}",
            message=f"Operator-triggered restart of {svc.container} on {svc.node}",
            priority="default",
            tags="arrows_counterclockwise",
        )
    return {
        "service_id": service_id,
        "success": rem.success,
        "duration_ms": rem.duration_ms,
        "error": rem.error,
        "control_plane": control_plane_snapshot(),
    }


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> str:
    lines: list[str] = []
    lines.append("# HELP athanor_watchdog_check_status 1 if last check passed, 0 if failed, -1 if unknown")
    lines.append("# TYPE athanor_watchdog_check_status gauge")
    for svc in SERVICES:
        st = state[svc.service_id]
        value = 1 if st.status == "OK" else (0 if st.status == "CRIT" else -1)
        lines.append(f'athanor_watchdog_check_status{{service="{svc.service_id}",node="{svc.node}"}} {value}')

    lines.append("# HELP athanor_watchdog_check_latency_ms Last probe latency")
    lines.append("# TYPE athanor_watchdog_check_latency_ms gauge")
    for svc in SERVICES:
        st = state[svc.service_id]
        lines.append(f'athanor_watchdog_check_latency_ms{{service="{svc.service_id}"}} {st.last_latency_ms}')

    lines.append("# HELP athanor_watchdog_consecutive_failures Current consecutive failure count")
    lines.append("# TYPE athanor_watchdog_consecutive_failures gauge")
    for svc in SERVICES:
        st = state[svc.service_id]
        lines.append(f'athanor_watchdog_consecutive_failures{{service="{svc.service_id}"}} {st.consecutive_failures}')

    lines.append("# HELP athanor_watchdog_total_checks Total checks since startup")
    lines.append("# TYPE athanor_watchdog_total_checks counter")
    for svc in SERVICES:
        st = state[svc.service_id]
        lines.append(f'athanor_watchdog_total_checks{{service="{svc.service_id}"}} {st.total_checks}')

    lines.append("# HELP athanor_watchdog_total_failures Total failed checks since startup")
    lines.append("# TYPE athanor_watchdog_total_failures counter")
    for svc in SERVICES:
        st = state[svc.service_id]
        lines.append(f'athanor_watchdog_total_failures{{service="{svc.service_id}"}} {st.total_failures}')

    lines.append("# HELP athanor_watchdog_total_remediations Total auto-remediations since startup")
    lines.append("# TYPE athanor_watchdog_total_remediations counter")
    for svc in SERVICES:
        st = state[svc.service_id]
        lines.append(f'athanor_watchdog_total_remediations{{service="{svc.service_id}"}} {st.total_remediations}')

    lines.append("# HELP athanor_watchdog_paused 1 if auto-remediation is paused, 0 otherwise")
    lines.append("# TYPE athanor_watchdog_paused gauge")
    lines.append(f"athanor_watchdog_paused {1 if PAUSED else 0}")

    lines.append("# HELP athanor_watchdog_mutation_gate_open 1 if runtime mutation is permitted, 0 otherwise")
    lines.append("# TYPE athanor_watchdog_mutation_gate_open gauge")
    lines.append(f"athanor_watchdog_mutation_gate_open {1 if mutation_gate_open() else 0}")

    lines.append("# HELP athanor_watchdog_auto_remediation_enabled 1 if automatic remediation is enabled, 0 otherwise")
    lines.append("# TYPE athanor_watchdog_auto_remediation_enabled gauge")
    lines.append(f"athanor_watchdog_auto_remediation_enabled {1 if auto_remediation_enabled() else 0}")

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
