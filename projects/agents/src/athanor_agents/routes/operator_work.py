"""Operator work routes for inbox, todos, ideas, backlog, and runs."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from ..operator_contract import (
    build_operator_action,
    emit_operator_audit_event,
    require_operator_action,
)

router = APIRouter(prefix="/v1/operator", tags=["operator-work"])


async def _load_operator_body(
    request: Request,
    *,
    route: str,
    action_class: str,
    default_reason: str,
):
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    if not isinstance(body, dict):
        body = {}

    candidate = build_operator_action(body, default_reason=default_reason)
    try:
        action = require_operator_action(body, action_class=action_class, default_reason=default_reason)
    except Exception as exc:
        detail = getattr(exc, "detail", str(exc))
        status_code = getattr(exc, "status_code", 400)
        await emit_operator_audit_event(
            service="agent-server",
            route=route,
            action_class=action_class,
            decision="denied",
            status_code=status_code,
            action=candidate,
            detail=str(detail),
        )
        return None, None, JSONResponse(status_code=status_code, content={"error": detail})
    return body, action, None


@router.get("/summary")
async def get_operator_work_summary():
    from ..operator_work import (
        approval_stats,
        backlog_stats,
        digest_summary,
        idea_stats,
        inbox_stats,
        output_summary,
        pattern_summary,
        project_summary,
        run_stats,
        todo_stats,
    )
    from ..bootstrap_state import build_bootstrap_runtime_snapshot
    from ..governance_state import build_governance_snapshot
    from ..tasks import get_task_stats

    (
        ideas,
        inbox,
        todos,
        backlog,
        runs,
        approvals,
        tasks,
        bootstrap,
        governance,
        digest,
        projects,
        outputs,
        patterns,
    ) = await asyncio.gather(
        idea_stats(),
        inbox_stats(),
        todo_stats(),
        backlog_stats(),
        run_stats(),
        approval_stats(),
        get_task_stats(),
        build_bootstrap_runtime_snapshot(include_snapshot_write=False),
        build_governance_snapshot(),
        digest_summary(),
        project_summary(),
        output_summary(),
        pattern_summary(),
    )

    return {
        "ideas": ideas,
        "inbox": inbox,
        "todos": todos,
        "backlog": backlog,
        "runs": runs,
        "approvals": approvals,
        "tasks": tasks,
        "bootstrap": bootstrap,
        "governance": governance,
        "digest": digest,
        "projects": projects,
        "outputs": outputs,
        "patterns": patterns,
    }


@router.get("/todos")
async def get_operator_todos(status: str = "", limit: int = 50):
    from ..operator_work import list_todos

    todos = await list_todos(status=status, limit=limit)
    return {"todos": todos, "count": len(todos)}


@router.post("/todos")
async def create_operator_todo_endpoint(request: Request):
    from ..operator_work import create_todo

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/operator/todos",
        action_class="operator",
        default_reason="Created operator todo",
    )
    if denial:
        return denial

    title = str(body.get("title") or "").strip()
    if not title:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/operator/todos",
            action_class="operator",
            decision="denied",
            status_code=400,
            action=action,
            detail="title is required",
        )
        return JSONResponse(status_code=400, content={"error": "title is required"})

    todo = await create_todo(
        title=title,
        description=str(body.get("description") or ""),
        category=str(body.get("category") or "ops"),
        scope_type=str(body.get("scope_type") or "global"),
        scope_id=str(body.get("scope_id") or "athanor"),
        priority=int(body.get("priority") or 3),
        energy_class=str(body.get("energy_class") or "focused"),
        due_at=body.get("due_at"),
        linked_goal_ids=body.get("linked_goal_ids") if isinstance(body.get("linked_goal_ids"), list) else [],
        linked_inbox_ids=body.get("linked_inbox_ids") if isinstance(body.get("linked_inbox_ids"), list) else [],
        origin=str(body.get("origin") or "operator"),
        created_by=str(body.get("actor") or action.actor or "operator"),
        metadata=dict(body.get("metadata") or {}) if isinstance(body.get("metadata"), dict) or body.get("metadata") is None else {},
    )
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/operator/todos",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Created operator todo {todo['id']}",
        target=todo["id"],
        metadata={"category": todo["category"], "scope_type": todo["scope_type"]},
    )
    return {"status": "created", "todo": todo}


@router.post("/todos/{todo_id}/transition")
async def transition_operator_todo_endpoint(todo_id: str, request: Request):
    from ..operator_work import transition_todo

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/operator/todos/{todo_id}/transition",
        action_class="operator",
        default_reason=f"Transitioned operator todo {todo_id}",
    )
    if denial:
        return denial

    try:
        todo = await transition_todo(
            todo_id,
            status=str(body.get("status") or ""),
            note=str(body.get("note") or ""),
        )
    except ValueError as exc:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/operator/todos/{todo_id}/transition",
            action_class="operator",
            decision="denied",
            status_code=400,
            action=action,
            detail=str(exc),
            target=todo_id,
        )
        return JSONResponse(status_code=400, content={"error": str(exc)})

    if not todo:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/operator/todos/{todo_id}/transition",
            action_class="operator",
            decision="denied",
            status_code=404,
            action=action,
            detail=f"Todo {todo_id} not found",
            target=todo_id,
        )
        return JSONResponse(status_code=404, content={"error": f"Todo '{todo_id}' not found"})

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/operator/todos/{todo_id}/transition",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Transitioned operator todo {todo_id} to {todo['status']}",
        target=todo_id,
        metadata={"status": todo["status"]},
    )
    return {"status": "updated", "todo": todo}


@router.get("/inbox")
async def get_operator_inbox(status: str = "", limit: int = 50):
    from ..operator_work import list_inbox

    items = await list_inbox(status=status, limit=limit)
    return {"items": items, "count": len(items)}


@router.post("/inbox")
async def create_operator_inbox_endpoint(request: Request):
    from ..operator_work import create_inbox_item

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/operator/inbox",
        action_class="operator",
        default_reason="Created operator inbox item",
    )
    if denial:
        return denial

    title = str(body.get("title") or "").strip()
    kind = str(body.get("kind") or "").strip()
    if not title or not kind:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/operator/inbox",
            action_class="operator",
            decision="denied",
            status_code=400,
            action=action,
            detail="kind and title are required",
        )
        return JSONResponse(status_code=400, content={"error": "kind and title are required"})

    item = await create_inbox_item(
        kind=kind,
        title=title,
        description=str(body.get("description") or ""),
        severity=int(body.get("severity") or 1),
        source=str(body.get("source") or "operator"),
        requires_decision=bool(body.get("requires_decision", False)),
        decision_type=str(body.get("decision_type") or ""),
        related_run_id=str(body.get("related_run_id") or ""),
        related_task_id=str(body.get("related_task_id") or ""),
        related_project_id=str(body.get("related_project_id") or ""),
        related_domain_id=str(body.get("related_domain_id") or ""),
        snooze_until=body.get("snooze_until"),
        metadata=dict(body.get("metadata") or {}) if isinstance(body.get("metadata"), dict) or body.get("metadata") is None else {},
    )
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/operator/inbox",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Created operator inbox item {item['id']}",
        target=item["id"],
        metadata={"kind": item["kind"], "severity": item["severity"]},
    )
    return {"status": "created", "item": item}


@router.post("/inbox/{inbox_id}/ack")
async def acknowledge_operator_inbox_endpoint(inbox_id: str, request: Request):
    from ..operator_work import acknowledge_inbox_item

    _, action, denial = await _load_operator_body(
        request,
        route="/v1/operator/inbox/{inbox_id}/ack",
        action_class="operator",
        default_reason=f"Acknowledged inbox item {inbox_id}",
    )
    if denial:
        return denial

    item = await acknowledge_inbox_item(inbox_id)
    if not item:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/operator/inbox/{inbox_id}/ack",
            action_class="operator",
            decision="denied",
            status_code=404,
            action=action,
            detail=f"Inbox item {inbox_id} not found",
            target=inbox_id,
        )
        return JSONResponse(status_code=404, content={"error": f"Inbox item '{inbox_id}' not found"})

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/operator/inbox/{inbox_id}/ack",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Acknowledged inbox item {inbox_id}",
        target=inbox_id,
    )
    return {"status": "updated", "item": item}


@router.post("/inbox/{inbox_id}/snooze")
async def snooze_operator_inbox_endpoint(inbox_id: str, request: Request):
    from ..operator_work import snooze_inbox_item

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/operator/inbox/{inbox_id}/snooze",
        action_class="operator",
        default_reason=f"Snoozed inbox item {inbox_id}",
    )
    if denial:
        return denial

    item = await snooze_inbox_item(inbox_id, until=body.get("until"))
    if not item:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/operator/inbox/{inbox_id}/snooze",
            action_class="operator",
            decision="denied",
            status_code=404,
            action=action,
            detail=f"Inbox item {inbox_id} not found",
            target=inbox_id,
        )
        return JSONResponse(status_code=404, content={"error": f"Inbox item '{inbox_id}' not found"})

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/operator/inbox/{inbox_id}/snooze",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Snoozed inbox item {inbox_id}",
        target=inbox_id,
    )
    return {"status": "updated", "item": item}


@router.post("/inbox/{inbox_id}/resolve")
async def resolve_operator_inbox_endpoint(inbox_id: str, request: Request):
    from ..operator_work import resolve_inbox_item

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/operator/inbox/{inbox_id}/resolve",
        action_class="operator",
        default_reason=f"Resolved inbox item {inbox_id}",
    )
    if denial:
        return denial

    item = await resolve_inbox_item(inbox_id, note=str(body.get("note") or ""))
    if not item:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/operator/inbox/{inbox_id}/resolve",
            action_class="operator",
            decision="denied",
            status_code=404,
            action=action,
            detail=f"Inbox item {inbox_id} not found",
            target=inbox_id,
        )
        return JSONResponse(status_code=404, content={"error": f"Inbox item '{inbox_id}' not found"})

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/operator/inbox/{inbox_id}/resolve",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Resolved inbox item {inbox_id}",
        target=inbox_id,
    )
    return {"status": "updated", "item": item}


@router.post("/inbox/{inbox_id}/convert")
async def convert_operator_inbox_endpoint(inbox_id: str, request: Request):
    from ..operator_work import convert_inbox_item_to_todo

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/operator/inbox/{inbox_id}/convert",
        action_class="operator",
        default_reason=f"Converted inbox item {inbox_id} to todo",
    )
    if denial:
        return denial

    payload = await convert_inbox_item_to_todo(
        inbox_id,
        category=str(body.get("category") or "decision"),
        priority=int(body.get("priority") or 3),
        energy_class=str(body.get("energy_class") or "quick"),
    )
    if not payload:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/operator/inbox/{inbox_id}/convert",
            action_class="operator",
            decision="denied",
            status_code=404,
            action=action,
            detail=f"Inbox item {inbox_id} not found",
            target=inbox_id,
        )
        return JSONResponse(status_code=404, content={"error": f"Inbox item '{inbox_id}' not found"})

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/operator/inbox/{inbox_id}/convert",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Converted inbox item {inbox_id} to todo {payload['todo']['id']}",
        target=inbox_id,
        metadata={"todo_id": payload["todo"]["id"]},
    )
    return {"status": "converted", **payload}


@router.get("/ideas")
async def get_operator_ideas(status: str = "", limit: int = 50):
    from ..operator_work import list_ideas

    ideas = await list_ideas(status=status, limit=limit)
    return {"ideas": ideas, "count": len(ideas)}


@router.post("/ideas")
async def create_operator_idea_endpoint(request: Request):
    from ..operator_work import create_idea

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/operator/ideas",
        action_class="operator",
        default_reason="Created operator idea",
    )
    if denial:
        return denial

    title = str(body.get("title") or "").strip()
    if not title:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/operator/ideas",
            action_class="operator",
            decision="denied",
            status_code=400,
            action=action,
            detail="title is required",
        )
        return JSONResponse(status_code=400, content={"error": "title is required"})

    idea = await create_idea(
        title=title,
        note=str(body.get("note") or ""),
        tags=body.get("tags") if isinstance(body.get("tags"), list) else [],
        source=str(body.get("source") or "operator"),
        confidence=float(body.get("confidence") or 0.5),
        energy_class=str(body.get("energy_class") or "focused"),
        scope_guess=str(body.get("scope_guess") or "global"),
        next_review_at=body.get("next_review_at"),
        metadata=dict(body.get("metadata") or {}) if isinstance(body.get("metadata"), dict) or body.get("metadata") is None else {},
    )
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/operator/ideas",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Created operator idea {idea['id']}",
        target=idea["id"],
    )
    return {"status": "created", "idea": idea}


@router.post("/ideas/{idea_id}/promote")
async def promote_operator_idea_endpoint(idea_id: str, request: Request):
    from ..operator_work import promote_idea

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/operator/ideas/{idea_id}/promote",
        action_class="operator",
        default_reason=f"Promoted operator idea {idea_id}",
    )
    if denial:
        return denial

    payload = await promote_idea(
        idea_id,
        target=str(body.get("target") or "backlog"),
        owner_agent=str(body.get("owner_agent") or "coding-agent"),
        project_id=str(body.get("project_id") or ""),
    )
    if not payload:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/operator/ideas/{idea_id}/promote",
            action_class="operator",
            decision="denied",
            status_code=404,
            action=action,
            detail=f"Idea {idea_id} not found",
            target=idea_id,
        )
        return JSONResponse(status_code=404, content={"error": f"Idea '{idea_id}' not found"})

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/operator/ideas/{idea_id}/promote",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Promoted operator idea {idea_id} to {payload['target']}",
        target=idea_id,
        metadata={"target": payload["target"]},
    )
    return {"status": "promoted", **payload}


@router.get("/backlog")
async def get_operator_backlog(status: str = "", owner_agent: str = "", limit: int = 50):
    from ..operator_work import list_backlog

    backlog = await list_backlog(status=status, owner_agent=owner_agent, limit=limit)
    return {"backlog": backlog, "count": len(backlog)}


@router.post("/backlog")
async def create_operator_backlog_endpoint(request: Request):
    from ..operator_work import create_backlog_item

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/operator/backlog",
        action_class="operator",
        default_reason="Created operator backlog item",
    )
    if denial:
        return denial

    title = str(body.get("title") or "").strip()
    prompt = str(body.get("prompt") or "").strip()
    owner_agent = str(body.get("owner_agent") or "").strip()
    if not title or not prompt or not owner_agent:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/operator/backlog",
            action_class="operator",
            decision="denied",
            status_code=400,
            action=action,
            detail="title, prompt, and owner_agent are required",
        )
        return JSONResponse(status_code=400, content={"error": "title, prompt, and owner_agent are required"})

    backlog = await create_backlog_item(
        title=title,
        prompt=prompt,
        owner_agent=owner_agent,
        support_agents=body.get("support_agents") if isinstance(body.get("support_agents"), list) else [],
        scope_type=str(body.get("scope_type") or "global"),
        scope_id=str(body.get("scope_id") or "athanor"),
        work_class=str(body.get("work_class") or "project_build"),
        priority=int(body.get("priority") or 3),
        approval_mode=str(body.get("approval_mode") or "none"),
        dispatch_policy=str(body.get("dispatch_policy") or "planner_eligible"),
        preconditions=body.get("preconditions") if isinstance(body.get("preconditions"), list) else [],
        linked_goal_ids=body.get("linked_goal_ids") if isinstance(body.get("linked_goal_ids"), list) else [],
        linked_todo_ids=body.get("linked_todo_ids") if isinstance(body.get("linked_todo_ids"), list) else [],
        linked_idea_id=str(body.get("linked_idea_id") or ""),
        created_by=str(body.get("actor") or action.actor or "operator"),
        origin=str(body.get("origin") or "operator"),
        metadata=dict(body.get("metadata") or {}) if isinstance(body.get("metadata"), dict) or body.get("metadata") is None else {},
    )
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/operator/backlog",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Created operator backlog item {backlog['id']}",
        target=backlog["id"],
    )
    return {"status": "created", "backlog": backlog}


@router.post("/backlog/{backlog_id}/transition")
async def transition_operator_backlog_endpoint(backlog_id: str, request: Request):
    from ..operator_work import transition_backlog_item

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/operator/backlog/{backlog_id}/transition",
        action_class="operator",
        default_reason=f"Transitioned backlog item {backlog_id}",
    )
    if denial:
        return denial

    try:
        backlog = await transition_backlog_item(
            backlog_id,
            status=str(body.get("status") or ""),
            note=str(body.get("note") or ""),
            blocking_reason=str(body.get("blocking_reason") or ""),
        )
    except ValueError as exc:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/operator/backlog/{backlog_id}/transition",
            action_class="operator",
            decision="denied",
            status_code=400,
            action=action,
            detail=str(exc),
            target=backlog_id,
        )
        return JSONResponse(status_code=400, content={"error": str(exc)})

    if not backlog:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/operator/backlog/{backlog_id}/transition",
            action_class="operator",
            decision="denied",
            status_code=404,
            action=action,
            detail=f"Backlog item {backlog_id} not found",
            target=backlog_id,
        )
        return JSONResponse(status_code=404, content={"error": f"Backlog item '{backlog_id}' not found"})

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/operator/backlog/{backlog_id}/transition",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Transitioned backlog item {backlog_id} to {backlog['status']}",
        target=backlog_id,
        metadata={"status": backlog["status"]},
    )
    return {"status": "updated", "backlog": backlog}


@router.post("/backlog/{backlog_id}/dispatch")
async def dispatch_operator_backlog_endpoint(backlog_id: str, request: Request):
    from ..operator_work import dispatch_backlog_item

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/operator/backlog/{backlog_id}/dispatch",
        action_class="operator",
        default_reason=f"Dispatched backlog item {backlog_id}",
    )
    if denial:
        return denial

    payload = await dispatch_backlog_item(
        backlog_id,
        lane_override=str(body.get("lane_override") or ""),
        reason=str(body.get("reason") or ""),
    )
    if not payload:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/operator/backlog/{backlog_id}/dispatch",
            action_class="operator",
            decision="denied",
            status_code=404,
            action=action,
            detail=f"Backlog item {backlog_id} not found",
            target=backlog_id,
        )
        return JSONResponse(status_code=404, content={"error": f"Backlog item '{backlog_id}' not found"})

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/operator/backlog/{backlog_id}/dispatch",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Dispatched backlog item {backlog_id}",
        target=backlog_id,
        metadata={"task_id": payload["task"].get("id", ""), "status": payload["backlog"].get("status", "")},
    )
    return {"status": "dispatched", **payload}


@router.get("/runs")
async def get_operator_runs(status: str = "", agent: str = "", limit: int = 50):
    from ..operator_work import list_runs

    runs = await list_runs(status=status, agent=agent, limit=limit)
    return {"runs": runs, "count": len(runs)}


@router.get("/approvals")
async def get_operator_approvals(status: str = "", limit: int = 50):
    from ..operator_work import list_approvals

    approvals = await list_approvals(status=status, limit=limit)
    return {"approvals": approvals, "count": len(approvals)}


@router.post("/approvals/{approval_id}/approve")
async def approve_operator_approval_endpoint(approval_id: str, request: Request):
    from ..operator_work import get_approval
    from ..tasks import approve_task

    _, action, denial = await _load_operator_body(
        request,
        route="/v1/operator/approvals/{approval_id}/approve",
        action_class="admin",
        default_reason=f"Approved operator approval {approval_id}",
    )
    if denial:
        return denial

    approval = await get_approval(approval_id)
    if not approval:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/operator/approvals/{approval_id}/approve",
            action_class="admin",
            decision="denied",
            status_code=404,
            action=action,
            detail=f"Approval {approval_id} not found",
            target=approval_id,
        )
        return JSONResponse(status_code=404, content={"error": f"Approval '{approval_id}' not found"})

    if str(approval.get("status") or "") != "pending":
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/operator/approvals/{approval_id}/approve",
            action_class="admin",
            decision="denied",
            status_code=409,
            action=action,
            detail=f"Approval {approval_id} is not pending",
            target=approval_id,
            metadata={"status": approval.get("status", "")},
        )
        return JSONResponse(status_code=409, content={"error": f"Approval '{approval_id}' is not pending"})

    related_task_id = str(approval.get("related_task_id") or "")
    if not related_task_id:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/operator/approvals/{approval_id}/approve",
            action_class="admin",
            decision="denied",
            status_code=409,
            action=action,
            detail=f"Approval {approval_id} is not bridged to a task",
            target=approval_id,
        )
        return JSONResponse(status_code=409, content={"error": f"Approval '{approval_id}' cannot be executed from the operator lane"})

    if not await approve_task(related_task_id, decided_by=str(action.actor or "operator")):
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/operator/approvals/{approval_id}/approve",
            action_class="admin",
            decision="denied",
            status_code=409,
            action=action,
            detail=f"Task {related_task_id} could not be approved",
            target=approval_id,
            metadata={"related_task_id": related_task_id},
        )
        return JSONResponse(status_code=409, content={"error": f"Approval '{approval_id}' could not be approved"})

    updated = await get_approval(approval_id)
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/operator/approvals/{approval_id}/approve",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Approved operator approval {approval_id}",
        target=approval_id,
        metadata={"related_task_id": related_task_id, "related_run_id": approval.get("related_run_id", "")},
    )
    return {"status": "approved", "approval": updated or approval}


@router.post("/approvals/{approval_id}/reject")
async def reject_operator_approval_endpoint(approval_id: str, request: Request):
    from ..operator_work import get_approval
    from ..tasks import reject_task

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/operator/approvals/{approval_id}/reject",
        action_class="admin",
        default_reason=f"Rejected operator approval {approval_id}",
    )
    if denial:
        return denial

    approval = await get_approval(approval_id)
    if not approval:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/operator/approvals/{approval_id}/reject",
            action_class="admin",
            decision="denied",
            status_code=404,
            action=action,
            detail=f"Approval {approval_id} not found",
            target=approval_id,
        )
        return JSONResponse(status_code=404, content={"error": f"Approval '{approval_id}' not found"})

    if str(approval.get("status") or "") != "pending":
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/operator/approvals/{approval_id}/reject",
            action_class="admin",
            decision="denied",
            status_code=409,
            action=action,
            detail=f"Approval {approval_id} is not pending",
            target=approval_id,
            metadata={"status": approval.get("status", "")},
        )
        return JSONResponse(status_code=409, content={"error": f"Approval '{approval_id}' is not pending"})

    related_task_id = str(approval.get("related_task_id") or "")
    if not related_task_id:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/operator/approvals/{approval_id}/reject",
            action_class="admin",
            decision="denied",
            status_code=409,
            action=action,
            detail=f"Approval {approval_id} is not bridged to a task",
            target=approval_id,
        )
        return JSONResponse(status_code=409, content={"error": f"Approval '{approval_id}' cannot be rejected from the operator lane"})

    if not await reject_task(
        related_task_id,
        reason=str(body.get("reason") or action.reason or f"Rejected operator approval {approval_id}"),
        decided_by=str(action.actor or "operator"),
    ):
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/operator/approvals/{approval_id}/reject",
            action_class="admin",
            decision="denied",
            status_code=409,
            action=action,
            detail=f"Task {related_task_id} could not be rejected",
            target=approval_id,
            metadata={"related_task_id": related_task_id},
        )
        return JSONResponse(status_code=409, content={"error": f"Approval '{approval_id}' could not be rejected"})

    updated = await get_approval(approval_id)
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/operator/approvals/{approval_id}/reject",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Rejected operator approval {approval_id}",
        target=approval_id,
        metadata={"related_task_id": related_task_id, "related_run_id": approval.get("related_run_id", "")},
    )
    return {"status": "rejected", "approval": updated or approval}
