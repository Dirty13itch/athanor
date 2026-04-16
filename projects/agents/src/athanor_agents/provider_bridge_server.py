from __future__ import annotations

import os
import time
from dataclasses import replace
from datetime import datetime, timezone

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .operator_contract import (
    build_operator_action,
    emit_operator_audit_event,
    require_operator_action,
)
from .provider_execution import (
    _build_direct_cli_command,
    _build_local_adapter_record,
    _bundle_prompt,
    _run_direct_cli,
)
from .subscriptions import get_policy_snapshot, get_provider_catalog_snapshot

app = FastAPI(title="Athanor Provider Bridge", version="0.1.0")
SERVICE_STARTED_AT = datetime.now(timezone.utc).isoformat()
SERVICE_NAME = "provider-bridge"


def _bridge_token() -> str:
    return os.getenv("ATHANOR_PROVIDER_BRIDGE_TOKEN", "").strip()


def _authorize(request: Request) -> None:
    required = _bridge_token()
    if not required:
        return

    header = request.headers.get("authorization", "")
    if header != f"Bearer {required}":
        raise HTTPException(status_code=401, detail="Unauthorized provider bridge request")


def _bridge_action_payload(body: dict[str, object]) -> dict[str, object]:
    payload = body.get("operator_action")
    if isinstance(payload, dict):
        return dict(payload)
    return body


def _build_bridge_action(body: dict[str, object], *, default_reason: str):
    requester = str(body.get("requester") or "provider-bridge").strip() or "provider-bridge"
    payload = _bridge_action_payload(body)
    action = build_operator_action(payload, default_actor=requester, default_reason=default_reason)
    if not action.session_id:
        action = replace(action, session_id=str(body.get("handoff_id") or requester))
    return action


async def _load_bridge_action(
    body: dict[str, object],
    *,
    route: str,
    action_class: str,
    default_reason: str,
):
    payload = _bridge_action_payload(body)
    candidate = _build_bridge_action(body, default_reason=default_reason)
    requester = str(body.get("requester") or "provider-bridge").strip() or "provider-bridge"
    try:
        action = require_operator_action(
            payload,
            action_class=action_class,
            default_actor=requester,
            default_reason=default_reason,
        )
    except Exception as exc:
        detail = getattr(exc, "detail", str(exc))
        status_code = getattr(exc, "status_code", 400)
        await emit_operator_audit_event(
            service=SERVICE_NAME,
            route=route,
            action_class=action_class,
            decision="denied",
            status_code=status_code,
            action=candidate,
            detail=str(detail),
            target=str(body.get("handoff_id") or body.get("provider") or "").strip() or None,
        )
        return None, JSONResponse(status_code=status_code, content={"error": detail})

    if not action.session_id:
        action = replace(action, session_id=str(body.get("handoff_id") or requester))
    return action, None


def _build_bundle_payload(body: dict[str, object]) -> dict[str, object]:
    prompt_mode = str(body.get("prompt_mode") or "raw")
    requested_workspace = str(body.get("workspace_dir") or "").strip()
    default_workspace = os.getenv("ATHANOR_PROVIDER_WORKSPACE_DIR", "C:\\Athanor")
    workspace_dir = requested_workspace or default_workspace
    workspace_path = Path(workspace_dir)
    # Remote governor requests may carry Linux container paths; bridge them back to the
    # canonical DESK workspace when the requested path is not meaningful on this host.
    if not workspace_dir or workspace_dir.startswith("/") or not workspace_path.exists():
        workspace_dir = default_workspace
    return {
        "id": str(body.get("handoff_id") or f"bridge-{int(time.time())}"),
        "provider": str(body.get("provider") or ""),
        "requester": str(body.get("requester") or "bridge"),
        "task_class": str(body.get("task_class") or "task"),
        "policy_class": str(body.get("policy_class") or "cloud_safe"),
        "meta_lane": str(body.get("meta_lane") or "frontier_cloud"),
        "prompt": str(body.get("prompt") or ""),
        "prompt_mode": prompt_mode,
        "abstract_prompt": str(body.get("abstract_prompt") or "") if prompt_mode == "abstracted" else None,
        "plan_packet": {
            "workspace_dir": workspace_dir
        },
    }


def build_health_snapshot() -> dict[str, object]:
    checked_at = datetime.now(timezone.utc).isoformat()
    policy = get_policy_snapshot()
    catalog = get_provider_catalog_snapshot(policy_only=True)
    providers = dict(policy.get("providers") or {})
    token_configured = bool(_bridge_token())
    dependencies = [
        {
            "id": "provider_policy",
            "status": "healthy" if providers else "degraded",
            "required": True,
            "last_checked_at": checked_at,
            "detail": f"{len(providers)} providers in the active routing policy",
        },
        {
            "id": "bridge_auth",
            "status": "healthy" if token_configured else "degraded",
            "required": False,
            "last_checked_at": checked_at,
            "detail": "Bearer token configured for bridge access" if token_configured else "Bridge token unset; running in local trust mode",
        },
    ]
    degraded = any(dependency["status"] != "healthy" for dependency in dependencies if dependency["required"])
    if not token_configured:
        degraded = True
    return {
        "service": SERVICE_NAME,
        "version": app.version,
        "status": "degraded" if degraded else "healthy",
        "auth_class": "admin" if token_configured else "read-only",
        "dependencies": dependencies,
        "last_error": None if not degraded else "Provider bridge is missing bridge auth or active policy truth is unavailable.",
        "started_at": SERVICE_STARTED_AT,
        "actions_allowed": ["provider.providers.read", "provider.execute"],
        "provider_count": len(providers),
        "policy_source": policy.get("policy_source"),
        "catalog_version": catalog.get("version"),
        "catalog_source": catalog.get("source_of_truth"),
        "bridge_host": "desk",
    }


@app.get("/health")
async def health():
    return build_health_snapshot()


@app.get("/v1/provider-bridge/providers")
async def providers(request: Request):
    _authorize(request)
    policy = get_policy_snapshot()
    catalog = get_provider_catalog_snapshot(policy_only=True)
    items = []
    policy_providers = dict(policy.get("providers") or {})
    for provider_entry in catalog.get("providers", []):
        provider_id = str(provider_entry.get("id") or "").strip()
        if not provider_id:
            continue
        provider_meta = dict(policy_providers.get(provider_id) or {})
        adapter = _build_local_adapter_record(provider_id, provider_meta, catalog_meta=dict(provider_entry))
        adapter["bridge_host"] = "desk"
        adapter["bridge_checked_at"] = datetime.now(timezone.utc).isoformat()
        items.append(adapter)
    items.sort(key=lambda item: item["provider"])
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "detail": "DESK provider bridge inventory generated from local CLI probes.",
        "policy_source": policy.get("policy_source"),
        "catalog_version": catalog.get("version"),
        "catalog_source": catalog.get("source_of_truth"),
        "providers": items,
        "count": len(items),
    }


@app.post("/v1/provider-bridge/execute")
async def execute(request: Request):
    body = await request.json()
    if not isinstance(body, dict):
        return JSONResponse(status_code=400, content={"error": "JSON object body required"})
    candidate = _build_bridge_action(body, default_reason="Executed provider bridge request")
    try:
        _authorize(request)
    except HTTPException as exc:
        await emit_operator_audit_event(
            service=SERVICE_NAME,
            route="/v1/provider-bridge/execute",
            action_class="admin",
            decision="denied",
            status_code=exc.status_code,
            action=candidate,
            detail=str(exc.detail),
            target=str(body.get("handoff_id") or body.get("provider") or "").strip() or None,
        )
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    provider = str(body.get("provider") or "")
    if not provider:
        await emit_operator_audit_event(
            service=SERVICE_NAME,
            route="/v1/provider-bridge/execute",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=candidate,
            detail="Field 'provider' is required",
        )
        return JSONResponse(status_code=400, content={"error": "Field 'provider' is required"})

    action, denial = await _load_bridge_action(
        body,
        route="/v1/provider-bridge/execute",
        action_class="admin",
        default_reason=f"Executed provider bridge request for {provider}",
    )
    if denial:
        return denial

    policy = get_policy_snapshot()
    provider_meta = dict(policy.get("providers", {}).get(provider, {}))
    adapter = _build_local_adapter_record(provider, provider_meta)
    if adapter["execution_mode"] != "direct_cli" or not adapter["adapter_available"]:
        await emit_operator_audit_event(
            service=SERVICE_NAME,
            route="/v1/provider-bridge/execute",
            action_class="admin",
            decision="denied",
            status_code=409,
            action=action,
            detail=f"Provider '{provider}' is not directly executable on this bridge host.",
            target=str(body.get("handoff_id") or provider),
            metadata={"provider": provider, "execution_mode": str(adapter.get("execution_mode") or "")},
        )
        return JSONResponse(
            status_code=409,
            content={
                "error": f"Provider '{provider}' is not directly executable on this bridge host.",
                "adapter": adapter,
            },
        )

    bundle = _build_bundle_payload(dict(body))
    command, cwd, stdin_text = _build_direct_cli_command(provider, str(adapter.get("command_hint") or ""), bundle)
    timeout_seconds = int(body.get("timeout_seconds") or 90)
    execution = await _run_direct_cli(
        command,
        cwd=cwd,
        timeout_seconds=timeout_seconds,
        stdin_text=stdin_text,
    )
    execution.update(
        {
            "provider": provider,
            "requester": bundle["requester"],
            "task_class": bundle["task_class"],
            "policy_class": bundle["policy_class"],
            "meta_lane": bundle["meta_lane"],
            "prompt_mode": bundle["prompt_mode"],
            "prompt_preview": _bundle_prompt(bundle)[:200],
            "execution_mode": "bridge_cli",
            "bridge_host": "desk",
            "handoff_id": bundle["id"],
            "lease_id": body.get("lease_id"),
            "command": command,
            "cwd": cwd,
            "stdin_mode": "pipe" if stdin_text is not None else "argument",
            "bridge_checked_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    await emit_operator_audit_event(
        service=SERVICE_NAME,
        route="/v1/provider-bridge/execute",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=str(execution.get("summary") or "Executed provider bridge request"),
        target=str(body.get("handoff_id") or provider),
        metadata={
            "provider": provider,
            "requester": str(bundle["requester"]),
            "task_class": str(bundle["task_class"]),
            "execution_mode": "bridge_cli",
            "result_ok": bool(execution.get("ok")),
        },
    )
    return execution
