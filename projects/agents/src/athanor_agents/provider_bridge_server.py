from __future__ import annotations

import os
import time
from datetime import datetime, timezone

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .provider_execution import (
    _build_direct_cli_command,
    _build_local_adapter_record,
    _bundle_prompt,
    _run_direct_cli,
)
from .subscriptions import get_policy_snapshot

app = FastAPI(title="Athanor Provider Bridge", version="0.1.0")


def _bridge_token() -> str:
    return os.getenv("ATHANOR_PROVIDER_BRIDGE_TOKEN", "").strip()


def _authorize(request: Request) -> None:
    required = _bridge_token()
    if not required:
        return

    header = request.headers.get("authorization", "")
    if header != f"Bearer {required}":
        raise HTTPException(status_code=401, detail="Unauthorized provider bridge request")


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


@app.get("/health")
async def health():
    return {"status": "ok", "service": "provider-bridge"}


@app.get("/v1/provider-bridge/providers")
async def providers(request: Request):
    _authorize(request)
    policy = get_policy_snapshot()
    items = []
    for provider_id, provider_meta in dict(policy.get("providers") or {}).items():
        adapter = _build_local_adapter_record(provider_id, dict(provider_meta))
        adapter["bridge_host"] = "desk"
        adapter["bridge_checked_at"] = datetime.now(timezone.utc).isoformat()
        items.append(adapter)
    items.sort(key=lambda item: item["provider"])
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "detail": "DESK provider bridge inventory generated from local CLI probes.",
        "providers": items,
        "count": len(items),
    }


@app.post("/v1/provider-bridge/execute")
async def execute(request: Request):
    _authorize(request)
    body = await request.json()
    provider = str(body.get("provider") or "")
    if not provider:
        return JSONResponse(status_code=400, content={"error": "Field 'provider' is required"})

    policy = get_policy_snapshot()
    provider_meta = dict(policy.get("providers", {}).get(provider, {}))
    adapter = _build_local_adapter_record(provider, provider_meta)
    if adapter["execution_mode"] != "direct_cli" or not adapter["adapter_available"]:
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
    return execution
