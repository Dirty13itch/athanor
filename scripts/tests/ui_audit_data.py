#!/usr/bin/env python3
"""Canonical UI surface definitions for the Athanor audit loop."""

from __future__ import annotations

from typing import Any

CoverageStatus = str


def _default_status(local_checks: list[str], live_checks: list[str], manual_checklist: list[str]) -> CoverageStatus:
    if live_checks:
        return "covered-live"
    if local_checks:
        return "covered-automated"
    if manual_checklist:
        return "covered-manual"
    return "uncovered"


def surface(
    *,
    surface_id: str,
    title: str,
    product: str,
    surface_type: str,
    route_path: str | None = None,
    api_path: str | None = None,
    owned_apis: list[str] | None = None,
    primary_controls: list[str] | None = None,
    local_checks: list[str] | None = None,
    live_checks: list[str] | None = None,
    manual_checklist: list[str] | None = None,
    notes: str | None = None,
    coverage_status: CoverageStatus | None = None,
) -> dict[str, Any]:
    local = local_checks or []
    live = live_checks or []
    manual = manual_checklist or []
    status = coverage_status or _default_status(local, live, manual)
    return {
        "id": surface_id,
        "title": title,
        "product": product,
        "surfaceType": surface_type,
        "routePath": route_path,
        "apiPath": api_path,
        "ownedApis": owned_apis or [],
        "primaryControls": primary_controls or [],
        "localChecks": local,
        "liveChecks": live,
        "manualChecklist": manual,
        "coverageStatus": status,
        "notes": notes,
    }


def route_surface(
    *,
    surface_id: str,
    title: str,
    product: str,
    route_path: str,
    owned_apis: list[str],
    primary_controls: list[str],
    local_checks: list[str],
    live_checks: list[str] | None = None,
    manual_checklist: list[str] | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    return surface(
        surface_id=surface_id,
        title=title,
        product=product,
        surface_type="route",
        route_path=route_path,
        owned_apis=owned_apis,
        primary_controls=primary_controls,
        local_checks=local_checks,
        live_checks=live_checks or [],
        manual_checklist=manual_checklist,
        notes=notes,
    )


def api_surface(
    *,
    surface_id: str,
    title: str,
    product: str,
    api_path: str,
    primary_controls: list[str],
    local_checks: list[str],
    live_checks: list[str] | None = None,
    manual_checklist: list[str] | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    return surface(
        surface_id=surface_id,
        title=title,
        product=product,
        surface_type="api",
        api_path=api_path,
        primary_controls=primary_controls,
        local_checks=local_checks,
        live_checks=live_checks or [],
        manual_checklist=manual_checklist,
        notes=notes,
    )


def workflow_surface(
    *,
    surface_id: str,
    title: str,
    product: str,
    route_path: str | None,
    owned_apis: list[str],
    primary_controls: list[str],
    local_checks: list[str],
    live_checks: list[str] | None = None,
    manual_checklist: list[str] | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    return surface(
        surface_id=surface_id,
        title=title,
        product=product,
        surface_type="workflow",
        route_path=route_path,
        owned_apis=owned_apis,
        primary_controls=primary_controls,
        local_checks=local_checks,
        live_checks=live_checks or [],
        manual_checklist=manual_checklist,
        notes=notes,
    )


DASHBOARD_ROUTE_BASE = ["projects/dashboard/tests/e2e/smoke-routes.spec.ts"]
DASHBOARD_ROUTE_LIVE = ["scripts/tests/live-dashboard-smoke.py::routes"]
DASHBOARD_API_BASE = ["projects/dashboard/tests/e2e/smoke-api.spec.ts"]
DASHBOARD_MUTATION_BASE = ["projects/dashboard/tests/e2e/mutations.spec.ts"]
EOQ_ROUTE_BASE = ["projects/eoq/tests/e2e/smoke.spec.ts"]
EOQ_WORKFLOW_BASE = ["projects/eoq/tests/e2e/gameplay.spec.ts"]
ULRICH_ROUTE_BASE = ["projects/ulrich-energy/tests/e2e/smoke.spec.ts"]
ULRICH_WORKFLOW_BASE = ["projects/ulrich-energy/tests/e2e/workflows.spec.ts"]


SURFACES: list[dict[str, Any]] = []


def _extend(items: list[dict[str, Any]]) -> None:
    SURFACES.extend(items)


_extend(
    [
        route_surface(
            surface_id="dashboard.route.command-center",
            title="Command Center",
            product="dashboard",
            route_path="/",
            owned_apis=["/api/overview"],
            primary_controls=["priority lane", "recent context", "project platform", "launchpad", "work planner"],
            local_checks=DASHBOARD_ROUTE_BASE + ["projects/dashboard/tests/e2e/navigation.spec.ts", "projects/dashboard/tests/e2e/consoles.spec.ts"],
            live_checks=DASHBOARD_ROUTE_LIVE + ["scripts/tests/live-dashboard-smoke.py::project-navigation"],
        ),
        route_surface(
            surface_id="dashboard.route.services",
            title="Services",
            product="dashboard",
            route_path="/services",
            owned_apis=["/api/services", "/api/services/history"],
            primary_controls=["status filters", "service drawer", "copy endpoint", "Grafana link"],
            local_checks=DASHBOARD_ROUTE_BASE + ["projects/dashboard/tests/e2e/operations.spec.ts"],
            live_checks=DASHBOARD_ROUTE_LIVE,
        ),
        route_surface(
            surface_id="dashboard.route.gpu",
            title="GPU Metrics",
            product="dashboard",
            route_path="/gpu",
            owned_apis=["/api/gpu", "/api/gpu/history"],
            primary_controls=["time range", "pin compare", "focus drill-down", "export"],
            local_checks=DASHBOARD_ROUTE_BASE + ["projects/dashboard/tests/e2e/operations.spec.ts", "projects/dashboard/tests/e2e/consoles.spec.ts"],
            live_checks=DASHBOARD_ROUTE_LIVE,
        ),
        route_surface(
            surface_id="dashboard.route.chat",
            title="Direct Chat",
            product="dashboard",
            route_path="/chat",
            owned_apis=["/api/models", "/api/chat", "/api/tts"],
            primary_controls=["session history", "prompt composer", "retry", "abort", "copy/export", "voice output"],
            local_checks=DASHBOARD_ROUTE_BASE + ["projects/dashboard/tests/e2e/consoles.spec.ts"],
            live_checks=DASHBOARD_ROUTE_LIVE + ["scripts/tests/live-dashboard-smoke.py::chat:workshop-worker", "scripts/tests/live-dashboard-smoke.py::chat:litellm-proxy"],
        ),
        route_surface(
            surface_id="dashboard.route.agents",
            title="Agents",
            product="dashboard",
            route_path="/agents",
            owned_apis=["/api/agents", "/api/chat"],
            primary_controls=["agent roster", "thread history", "tool timeline", "retry", "abort", "copy/export"],
            local_checks=DASHBOARD_ROUTE_BASE + ["projects/dashboard/tests/e2e/consoles.spec.ts"],
            live_checks=DASHBOARD_ROUTE_LIVE + ["scripts/tests/live-dashboard-smoke.py::chat:agent-server"],
        ),
        route_surface(
            surface_id="dashboard.route.tasks",
            title="Tasks",
            product="dashboard",
            route_path="/tasks",
            owned_apis=["/api/workforce", "/api/workforce/tasks"],
            primary_controls=["queue filters", "task composer", "approve", "cancel", "rerun"],
            local_checks=DASHBOARD_ROUTE_BASE + ["projects/dashboard/tests/e2e/mutations.spec.ts"],
            live_checks=DASHBOARD_ROUTE_LIVE,
        ),
        route_surface(
            surface_id="dashboard.route.goals",
            title="Goals",
            product="dashboard",
            route_path="/goals",
            owned_apis=["/api/workforce", "/api/workforce/goals"],
            primary_controls=["goal filters", "create goal", "delete goal", "project focus"],
            local_checks=DASHBOARD_ROUTE_BASE + ["projects/dashboard/tests/e2e/mutations.spec.ts"],
            live_checks=DASHBOARD_ROUTE_LIVE,
        ),
        route_surface(
            surface_id="dashboard.route.notifications",
            title="Notifications",
            product="dashboard",
            route_path="/notifications",
            owned_apis=["/api/workforce", "/api/workforce/notifications/:notificationId/resolve"],
            primary_controls=["approval lane", "resolve", "reject", "show resolved"],
            local_checks=DASHBOARD_ROUTE_BASE + ["projects/dashboard/tests/e2e/mutations.spec.ts"],
            live_checks=DASHBOARD_ROUTE_LIVE,
        ),
        route_surface(
            surface_id="dashboard.route.workplanner",
            title="Work Planner",
            product="dashboard",
            route_path="/workplanner",
            owned_apis=["/api/workforce", "/api/workforce/plan", "/api/workforce/redirect"],
            primary_controls=["project focus", "plan generation", "redirect", "task inspection"],
            local_checks=DASHBOARD_ROUTE_BASE + ["projects/dashboard/tests/e2e/consoles.spec.ts", "projects/dashboard/tests/e2e/mutations.spec.ts"],
            live_checks=DASHBOARD_ROUTE_LIVE + ["scripts/tests/live-dashboard-smoke.py::project-navigation"],
        ),
        route_surface(
            surface_id="dashboard.route.workspace",
            title="Workspace",
            product="dashboard",
            route_path="/workspace",
            owned_apis=["/api/workforce"],
            primary_controls=["broadcast lane", "endorse", "trust view", "workspace state"],
            local_checks=DASHBOARD_ROUTE_BASE + ["projects/dashboard/tests/e2e/consoles.spec.ts"],
            live_checks=DASHBOARD_ROUTE_LIVE,
        ),
        route_surface(
            surface_id="dashboard.route.activity",
            title="Activity Feed",
            product="dashboard",
            route_path="/activity",
            owned_apis=["/api/history", "/api/activity"],
            primary_controls=["project filter", "agent filter", "timeframe", "selection drawer", "review back-link"],
            local_checks=DASHBOARD_ROUTE_BASE + ["projects/dashboard/tests/e2e/family-flows.spec.ts"],
            live_checks=DASHBOARD_ROUTE_LIVE,
        ),
        route_surface(
            surface_id="dashboard.route.conversations",
            title="Conversations",
            product="dashboard",
            route_path="/conversations",
            owned_apis=["/api/history", "/api/conversations"],
            primary_controls=["thread filters", "detail drawer", "task back-link", "output back-link"],
            local_checks=DASHBOARD_ROUTE_BASE + ["projects/dashboard/tests/e2e/family-flows.spec.ts"],
            live_checks=DASHBOARD_ROUTE_LIVE,
        ),
        route_surface(
            surface_id="dashboard.route.gallery",
            title="Gallery",
            product="dashboard",
            route_path="/gallery",
            owned_apis=["/api/gallery/overview", "/api/comfyui/history", "/api/comfyui/image/[...path]"],
            primary_controls=["source filters", "preview drawer", "outputs back-link", "queue summary"],
            local_checks=DASHBOARD_ROUTE_BASE + ["projects/dashboard/tests/e2e/family-flows.spec.ts"],
            live_checks=DASHBOARD_ROUTE_LIVE,
        ),
        route_surface(
            surface_id="dashboard.route.home",
            title="Home",
            product="dashboard",
            route_path="/home",
            owned_apis=["/api/home/overview"],
            primary_controls=["setup ladder", "focused panel drawer", "open Home Assistant", "monitoring back-link"],
            local_checks=DASHBOARD_ROUTE_BASE + ["projects/dashboard/tests/e2e/family-flows.spec.ts"],
            live_checks=DASHBOARD_ROUTE_LIVE + ["scripts/tests/live-dashboard-smoke.py::drawer-launches"],
        ),
        route_surface(
            surface_id="dashboard.route.insights",
            title="Insights",
            product="dashboard",
            route_path="/insights",
            owned_apis=["/api/intelligence", "/api/insights", "/api/insights/run"],
            primary_controls=["severity filter", "run insights", "pattern review", "project filter"],
            local_checks=DASHBOARD_ROUTE_BASE + ["projects/dashboard/tests/e2e/family-flows.spec.ts", "projects/dashboard/tests/e2e/mutations.spec.ts"],
            live_checks=DASHBOARD_ROUTE_LIVE,
        ),
        route_surface(
            surface_id="dashboard.route.learning",
            title="Learning",
            product="dashboard",
            route_path="/learning",
            owned_apis=["/api/intelligence", "/api/learning/metrics", "/api/learning/improvement", "/api/learning/benchmarks"],
            primary_controls=["benchmark trigger", "improvement state", "trend cards", "agent filter"],
            local_checks=DASHBOARD_ROUTE_BASE + ["projects/dashboard/tests/e2e/family-flows.spec.ts", "projects/dashboard/tests/e2e/mutations.spec.ts"],
            live_checks=DASHBOARD_ROUTE_LIVE,
        ),
        route_surface(
            surface_id="dashboard.route.media",
            title="Media",
            product="dashboard",
            route_path="/media",
            owned_apis=["/api/media/overview"],
            primary_controls=["launch preview drawer", "queue summary", "library posture", "monitoring back-link"],
            local_checks=DASHBOARD_ROUTE_BASE + ["projects/dashboard/tests/e2e/family-flows.spec.ts"],
            live_checks=DASHBOARD_ROUTE_LIVE + ["scripts/tests/live-dashboard-smoke.py::drawer-launches"],
        ),
        route_surface(
            surface_id="dashboard.route.monitoring",
            title="Monitoring",
            product="dashboard",
            route_path="/monitoring",
            owned_apis=["/api/monitoring"],
            primary_controls=["node filter", "Grafana drawer", "refresh", "service cross-link"],
            local_checks=DASHBOARD_ROUTE_BASE + ["projects/dashboard/tests/e2e/family-flows.spec.ts"],
            live_checks=DASHBOARD_ROUTE_LIVE + ["scripts/tests/live-dashboard-smoke.py::drawer-launches"],
        ),
        route_surface(
            surface_id="dashboard.route.more",
            title="All Pages",
            product="dashboard",
            route_path="/more",
            owned_apis=[],
            primary_controls=["family index", "deep links", "round-trip navigation"],
            local_checks=DASHBOARD_ROUTE_BASE + ["projects/dashboard/tests/e2e/navigation.spec.ts"],
            live_checks=DASHBOARD_ROUTE_LIVE,
        ),
        route_surface(
            surface_id="dashboard.route.outputs",
            title="Outputs",
            product="dashboard",
            route_path="/outputs",
            owned_apis=["/api/history", "/api/outputs", "/api/outputs/[...path]"],
            primary_controls=["project filter", "preview drawer", "task back-links", "output asset links"],
            local_checks=DASHBOARD_ROUTE_BASE + ["projects/dashboard/tests/e2e/family-flows.spec.ts"],
            live_checks=DASHBOARD_ROUTE_LIVE,
            manual_checklist=["Verify binary asset download links against a live output artifact."],
        ),
        route_surface(
            surface_id="dashboard.route.personal-data",
            title="Personal Data",
            product="dashboard",
            route_path="/personal-data",
            owned_apis=["/api/memory", "/api/personal-data/stats", "/api/personal-data/search"],
            primary_controls=["semantic search", "entity drawer", "project filters", "project back-link"],
            local_checks=DASHBOARD_ROUTE_BASE + ["projects/dashboard/tests/e2e/family-flows.spec.ts"],
            live_checks=DASHBOARD_ROUTE_LIVE,
        ),
        route_surface(
            surface_id="dashboard.route.preferences",
            title="Preferences",
            product="dashboard",
            route_path="/preferences",
            owned_apis=["/api/memory", "/api/preferences", "/api/push/subscribe", "/api/push/send"],
            primary_controls=["store preference", "shared filters", "push manager", "project back-link"],
            local_checks=DASHBOARD_ROUTE_BASE + ["projects/dashboard/tests/e2e/family-flows.spec.ts", "projects/dashboard/tests/e2e/browser-integrations.spec.ts"],
            live_checks=DASHBOARD_ROUTE_LIVE,
        ),
        route_surface(
            surface_id="dashboard.route.review",
            title="Code Review",
            product="dashboard",
            route_path="/review",
            owned_apis=["/api/intelligence", "/api/workforce/tasks/:taskId/approve"],
            primary_controls=["selection drawer", "approve", "project filter", "project back-link"],
            local_checks=DASHBOARD_ROUTE_BASE + ["projects/dashboard/tests/e2e/family-flows.spec.ts", "projects/dashboard/tests/e2e/mutations.spec.ts"],
            live_checks=DASHBOARD_ROUTE_LIVE + ["scripts/tests/live-dashboard-smoke.py::project-navigation"],
        ),
        route_surface(
            surface_id="dashboard.route.terminal",
            title="Terminal",
            product="dashboard",
            route_path="/terminal",
            owned_apis=[],
            primary_controls=["node select", "websocket fallback", "connection state"],
            local_checks=DASHBOARD_ROUTE_BASE + ["projects/dashboard/tests/e2e/navigation.spec.ts"],
            live_checks=DASHBOARD_ROUTE_LIVE,
        ),
        route_surface(
            surface_id="dashboard.route.offline",
            title="Offline",
            product="dashboard",
            route_path="/offline",
            owned_apis=[],
            primary_controls=["offline message", "retry button"],
            local_checks=DASHBOARD_ROUTE_BASE,
            live_checks=[],
            manual_checklist=["Verify offline route via browser network throttling in a manual pass."],
        ),
    ]
)

_extend(
    [
        route_surface(surface_id="eoq.route.home", title="EoBQ Home", product="eoq", route_path="/", owned_apis=["/api/chat", "/api/choices", "/api/narrate", "/api/memory"], primary_controls=["start", "continue", "freeform input", "choice play"], local_checks=EOQ_ROUTE_BASE + EOQ_WORKFLOW_BASE, live_checks=["scripts/tests/live-eoq-smoke.py::routes"]),
        route_surface(surface_id="eoq.route.gallery", title="EoBQ Gallery", product="eoq", route_path="/gallery", owned_apis=["/api/gallery", "/api/generate"], primary_controls=["portrait filters", "preview modal", "generation history"], local_checks=EOQ_ROUTE_BASE + EOQ_WORKFLOW_BASE, live_checks=["scripts/tests/live-eoq-smoke.py::routes"]),
        route_surface(surface_id="eoq.route.references", title="EoBQ References", product="eoq", route_path="/references", owned_apis=["/api/references", "/api/references/[id]", "/api/references/[id]/photos"], primary_controls=["library filters", "persona add", "photo upload"], local_checks=EOQ_ROUTE_BASE + EOQ_WORKFLOW_BASE, live_checks=["scripts/tests/live-eoq-smoke.py::routes"]),
        api_surface(surface_id="eoq.api.chat", title="EoBQ Chat API", product="eoq", api_path="/api/chat", primary_controls=["dialogue SSE"], local_checks=EOQ_ROUTE_BASE, live_checks=["scripts/tests/live-eoq-smoke.py::dialogue"]),
        api_surface(surface_id="eoq.api.choices", title="EoBQ Choices API", product="eoq", api_path="/api/choices", primary_controls=["choice generation"], local_checks=EOQ_ROUTE_BASE, live_checks=["scripts/tests/live-eoq-smoke.py::choices"]),
        api_surface(surface_id="eoq.api.gallery", title="EoBQ Gallery API", product="eoq", api_path="/api/gallery", primary_controls=["gallery inventory"], local_checks=EOQ_ROUTE_BASE, live_checks=["scripts/tests/live-eoq-smoke.py::gallery"]),
        api_surface(surface_id="eoq.api.generate", title="EoBQ Generate API", product="eoq", api_path="/api/generate", primary_controls=["portrait generation"], local_checks=EOQ_ROUTE_BASE, manual_checklist=["Run the low-volume live generation smoke only when the generation surface changes."]),
        api_surface(surface_id="eoq.api.memory", title="EoBQ Memory API", product="eoq", api_path="/api/memory", primary_controls=["memory write and search"], local_checks=EOQ_ROUTE_BASE),
        api_surface(surface_id="eoq.api.narrate", title="EoBQ Narrate API", product="eoq", api_path="/api/narrate", primary_controls=["narration SSE"], local_checks=EOQ_ROUTE_BASE, live_checks=["scripts/tests/live-eoq-smoke.py::narrate"]),
        api_surface(surface_id="eoq.api.references", title="EoBQ References API", product="eoq", api_path="/api/references", primary_controls=["reference listing"], local_checks=EOQ_ROUTE_BASE, live_checks=["scripts/tests/live-eoq-smoke.py::references"]),
        api_surface(surface_id="eoq.api.reference-detail", title="EoBQ Reference Detail API", product="eoq", api_path="/api/references/[id]", primary_controls=["reference detail"], local_checks=EOQ_ROUTE_BASE, live_checks=["scripts/tests/live-eoq-smoke.py::reference-detail"]),
        api_surface(surface_id="eoq.api.reference-photos", title="EoBQ Reference Photos API", product="eoq", api_path="/api/references/[id]/photos", primary_controls=["photo upload and delete"], local_checks=EOQ_WORKFLOW_BASE, manual_checklist=["Use the local fixture upload/remove flow and a targeted live mutation check before shipping reference-upload changes."]),
        workflow_surface(surface_id="eoq.workflow.continue-and-overlays", title="EoBQ Continue and Overlay Loop", product="eoq", route_path="/", owned_apis=["/api/chat", "/api/narrate"], primary_controls=["continue", "log", "map", "explore", "settings"], local_checks=EOQ_WORKFLOW_BASE),
        workflow_surface(surface_id="eoq.workflow.dialogue-and-choice-loop", title="EoBQ Dialogue and Choice Loop", product="eoq", route_path="/", owned_apis=["/api/chat", "/api/choices"], primary_controls=["freeform player input", "choice selection", "scene continuation"], local_checks=EOQ_WORKFLOW_BASE, live_checks=["scripts/tests/live-eoq-smoke.py::dialogue"]),
        workflow_surface(surface_id="eoq.workflow.references-and-gallery", title="EoBQ References and Gallery Loop", product="eoq", route_path="/references", owned_apis=["/api/gallery", "/api/references"], primary_controls=["gallery filter", "persona add", "photo upload"], local_checks=EOQ_WORKFLOW_BASE, live_checks=["scripts/tests/live-eoq-smoke.py::references"]),
    ]
)

_extend(
    [
        route_surface(surface_id="ulrich.route.home", title="Ulrich Home", product="ulrich-energy", route_path="/", owned_apis=["/api/analytics/dashboard"], primary_controls=["quick actions", "summary cards", "report drill-down"], local_checks=ULRICH_ROUTE_BASE + ULRICH_WORKFLOW_BASE, live_checks=["scripts/tests/live-ulrich-smoke.py::routes"]),
        route_surface(surface_id="ulrich.route.analytics", title="Ulrich Analytics", product="ulrich-energy", route_path="/analytics", owned_apis=["/api/analytics/dashboard"], primary_controls=["dashboard summary", "slow-data resilience"], local_checks=ULRICH_ROUTE_BASE, live_checks=["scripts/tests/live-ulrich-smoke.py::routes"]),
        route_surface(surface_id="ulrich.route.clients", title="Ulrich Clients", product="ulrich-energy", route_path="/clients", owned_apis=["/api/clients"], primary_controls=["client list", "client drill-down"], local_checks=ULRICH_ROUTE_BASE, live_checks=["scripts/tests/live-ulrich-smoke.py::routes"]),
        route_surface(surface_id="ulrich.route.inspections", title="Ulrich Inspections", product="ulrich-energy", route_path="/inspections", owned_apis=["/api/inspections", "/api/inspections/[id]"], primary_controls=["inspection list", "detail navigation", "empty state"], local_checks=ULRICH_ROUTE_BASE + ULRICH_WORKFLOW_BASE, live_checks=["scripts/tests/live-ulrich-smoke.py::routes"]),
        route_surface(surface_id="ulrich.route.inspections-new", title="Ulrich New Inspection", product="ulrich-energy", route_path="/inspections/new", owned_apis=["/api/inspections"], primary_controls=["create inspection"], local_checks=ULRICH_ROUTE_BASE + ULRICH_WORKFLOW_BASE, manual_checklist=["Use the optional live mutation mode before shipping inspection-form changes."]),
        route_surface(surface_id="ulrich.route.projects", title="Ulrich Projects", product="ulrich-energy", route_path="/projects", owned_apis=["/api/projects"], primary_controls=["project drill-down", "status cards"], local_checks=ULRICH_ROUTE_BASE, live_checks=["scripts/tests/live-ulrich-smoke.py::routes"]),
        route_surface(surface_id="ulrich.route.reports", title="Ulrich Reports", product="ulrich-energy", route_path="/reports", owned_apis=["/api/reports", "/api/reports/[id]", "/api/reports/generate"], primary_controls=["report list", "report detail", "inspection back-link"], local_checks=ULRICH_ROUTE_BASE + ULRICH_WORKFLOW_BASE, live_checks=["scripts/tests/live-ulrich-smoke.py::routes"]),
        api_surface(surface_id="ulrich.api.analytics", title="Ulrich Analytics API", product="ulrich-energy", api_path="/api/analytics/dashboard", primary_controls=["analytics snapshot"], local_checks=ULRICH_ROUTE_BASE, live_checks=["scripts/tests/live-ulrich-smoke.py::analytics"]),
        api_surface(surface_id="ulrich.api.clients", title="Ulrich Clients API", product="ulrich-energy", api_path="/api/clients", primary_controls=["client list"], local_checks=ULRICH_ROUTE_BASE, live_checks=["scripts/tests/live-ulrich-smoke.py::clients"]),
        api_surface(surface_id="ulrich.api.inspections", title="Ulrich Inspections API", product="ulrich-energy", api_path="/api/inspections", primary_controls=["inspection list"], local_checks=ULRICH_ROUTE_BASE, live_checks=["scripts/tests/live-ulrich-smoke.py::inspections"]),
        api_surface(surface_id="ulrich.api.inspection-detail", title="Ulrich Inspection Detail API", product="ulrich-energy", api_path="/api/inspections/[id]", primary_controls=["inspection detail"], local_checks=ULRICH_ROUTE_BASE, live_checks=["scripts/tests/live-ulrich-smoke.py::inspection-detail"]),
        api_surface(surface_id="ulrich.api.projects", title="Ulrich Projects API", product="ulrich-energy", api_path="/api/projects", primary_controls=["project list"], local_checks=ULRICH_ROUTE_BASE, live_checks=["scripts/tests/live-ulrich-smoke.py::projects"]),
        api_surface(surface_id="ulrich.api.reports", title="Ulrich Reports API", product="ulrich-energy", api_path="/api/reports", primary_controls=["report list"], local_checks=ULRICH_ROUTE_BASE, live_checks=["scripts/tests/live-ulrich-smoke.py::reports"]),
        api_surface(surface_id="ulrich.api.report-detail", title="Ulrich Report Detail API", product="ulrich-energy", api_path="/api/reports/[id]", primary_controls=["report detail"], local_checks=ULRICH_ROUTE_BASE, live_checks=["scripts/tests/live-ulrich-smoke.py::report-detail"]),
        api_surface(surface_id="ulrich.api.reports-generate", title="Ulrich Reports Generate API", product="ulrich-energy", api_path="/api/reports/generate", primary_controls=["report generation"], local_checks=ULRICH_ROUTE_BASE + ULRICH_WORKFLOW_BASE, manual_checklist=["Use the optional live mutation mode before shipping report-generation changes."]),
        workflow_surface(surface_id="ulrich.workflow.create-inspection", title="Ulrich Create Inspection Flow", product="ulrich-energy", route_path="/inspections/new", owned_apis=["/api/inspections"], primary_controls=["create inspection and open detail"], local_checks=ULRICH_WORKFLOW_BASE),
        workflow_surface(surface_id="ulrich.workflow.generate-report", title="Ulrich Generate Report Flow", product="ulrich-energy", route_path="/inspections/[id]", owned_apis=["/api/reports/generate", "/api/reports/[id]"], primary_controls=["generate report and open report detail"], local_checks=ULRICH_WORKFLOW_BASE),
        workflow_surface(surface_id="ulrich.workflow.quick-actions", title="Ulrich Quick Actions and Return Navigation", product="ulrich-energy", route_path="/", owned_apis=["/api/reports", "/api/inspections/[id]"], primary_controls=["home quick actions", "report drill-down", "inspection back-link"], local_checks=ULRICH_WORKFLOW_BASE),
    ]
)

_extend(
    [
        workflow_surface(surface_id="integration.workflow.command-center-to-workplanner", title="Command Center to Work Planner", product="integration", route_path="/", owned_apis=["/api/overview", "/api/workforce"], primary_controls=["command center incident/workplanner navigation"], local_checks=["projects/dashboard/tests/e2e/navigation.spec.ts", "projects/dashboard/tests/e2e/family-flows.spec.ts"], live_checks=["scripts/tests/live-dashboard-smoke.py::project-navigation"]),
        workflow_surface(surface_id="integration.workflow.command-center-to-tenants", title="Command Center to Tenant Launches", product="integration", route_path="/", owned_apis=["/api/overview", "/api/projects"], primary_controls=["project card external launch", "tenant workspace deep links"], local_checks=["projects/dashboard/tests/e2e/consoles.spec.ts"], live_checks=["scripts/tests/run-live-ui-smoke.py::dashboard+tenants"], manual_checklist=["Check tenant launch links in the browser after any project-registry URL change."]),
        workflow_surface(surface_id="integration.workflow.domain-drawer-round-trip", title="Domain Drawer Round Trip", product="integration", route_path="/monitoring", owned_apis=["/api/monitoring", "/api/media/overview", "/api/home/overview", "/api/gallery/overview"], primary_controls=["drawer open", "external launch", "browser back restore"], local_checks=["projects/dashboard/tests/e2e/family-flows.spec.ts"], live_checks=["scripts/tests/live-dashboard-smoke.py::drawer-launches"]),
        workflow_surface(surface_id="integration.workflow.live-chat-stack", title="Live Chat Stack", product="integration", route_path="/chat", owned_apis=["/api/chat", "/api/models"], primary_controls=["worker direct chat", "LiteLLM routed chat", "agent handoff"], local_checks=["projects/dashboard/tests/e2e/consoles.spec.ts"], live_checks=["scripts/tests/live-dashboard-smoke.py::chat-results"]),
    ]
)

_extend(
    [
        api_surface(surface_id="dashboard.api.overview", title="Overview API", product="dashboard", api_path="/api/overview", primary_controls=["command center snapshot"], local_checks=DASHBOARD_API_BASE, live_checks=["scripts/tests/live-dashboard-smoke.py::api:/api/overview"]),
        api_surface(surface_id="dashboard.api.services", title="Services API", product="dashboard", api_path="/api/services", primary_controls=["service snapshot"], local_checks=DASHBOARD_API_BASE, live_checks=["scripts/tests/live-dashboard-smoke.py::api:/api/services"]),
        api_surface(surface_id="dashboard.api.services-history", title="Services History API", product="dashboard", api_path="/api/services/history", primary_controls=["service trend history"], local_checks=DASHBOARD_API_BASE, live_checks=["scripts/tests/live-dashboard-smoke.py::api:/api/services/history"]),
        api_surface(surface_id="dashboard.api.gpu", title="GPU API", product="dashboard", api_path="/api/gpu", primary_controls=["gpu snapshot"], local_checks=DASHBOARD_API_BASE, live_checks=["scripts/tests/live-dashboard-smoke.py::api:/api/gpu"]),
        api_surface(surface_id="dashboard.api.gpu-history", title="GPU History API", product="dashboard", api_path="/api/gpu/history", primary_controls=["gpu trend history"], local_checks=DASHBOARD_API_BASE, live_checks=["scripts/tests/live-dashboard-smoke.py::api:/api/gpu/history"]),
        api_surface(surface_id="dashboard.api.models", title="Models API", product="dashboard", api_path="/api/models", primary_controls=["model inventory"], local_checks=DASHBOARD_API_BASE, live_checks=["scripts/tests/live-dashboard-smoke.py::api:/api/models"]),
        api_surface(surface_id="dashboard.api.projects", title="Projects API", product="dashboard", api_path="/api/projects", primary_controls=["project registry"], local_checks=DASHBOARD_API_BASE, live_checks=["scripts/tests/live-dashboard-smoke.py::api:/api/projects"]),
        api_surface(surface_id="dashboard.api.workforce", title="Workforce API", product="dashboard", api_path="/api/workforce", primary_controls=["workforce snapshot"], local_checks=DASHBOARD_API_BASE, live_checks=["scripts/tests/live-dashboard-smoke.py::api:/api/workforce"]),
        api_surface(surface_id="dashboard.api.history", title="History API", product="dashboard", api_path="/api/history", primary_controls=["history family snapshot"], local_checks=DASHBOARD_API_BASE, live_checks=["scripts/tests/live-dashboard-smoke.py::api:/api/history"]),
        api_surface(surface_id="dashboard.api.intelligence", title="Intelligence API", product="dashboard", api_path="/api/intelligence", primary_controls=["intelligence family snapshot"], local_checks=DASHBOARD_API_BASE, live_checks=["scripts/tests/live-dashboard-smoke.py::api:/api/intelligence"]),
        api_surface(surface_id="dashboard.api.memory", title="Memory API", product="dashboard", api_path="/api/memory", primary_controls=["memory family snapshot"], local_checks=DASHBOARD_API_BASE, live_checks=["scripts/tests/live-dashboard-smoke.py::api:/api/memory"]),
        api_surface(surface_id="dashboard.api.monitoring", title="Monitoring API", product="dashboard", api_path="/api/monitoring", primary_controls=["monitoring snapshot"], local_checks=DASHBOARD_API_BASE, live_checks=["scripts/tests/live-dashboard-smoke.py::api:/api/monitoring"]),
        api_surface(surface_id="dashboard.api.media-overview", title="Media Overview API", product="dashboard", api_path="/api/media/overview", primary_controls=["media domain snapshot"], local_checks=DASHBOARD_API_BASE, live_checks=["scripts/tests/live-dashboard-smoke.py::api:/api/media/overview"]),
        api_surface(surface_id="dashboard.api.gallery-overview", title="Gallery Overview API", product="dashboard", api_path="/api/gallery/overview", primary_controls=["gallery domain snapshot"], local_checks=DASHBOARD_API_BASE, live_checks=["scripts/tests/live-dashboard-smoke.py::api:/api/gallery/overview"]),
        api_surface(surface_id="dashboard.api.home-overview", title="Home Overview API", product="dashboard", api_path="/api/home/overview", primary_controls=["home domain snapshot"], local_checks=DASHBOARD_API_BASE, live_checks=["scripts/tests/live-dashboard-smoke.py::api:/api/home/overview"]),
        api_surface(surface_id="dashboard.api.personal-data-search", title="Personal Data Search API", product="dashboard", api_path="/api/personal-data/search", primary_controls=["semantic search"], local_checks=DASHBOARD_API_BASE, live_checks=["scripts/tests/live-dashboard-smoke.py::api:/api/personal-data/search"]),
        api_surface(surface_id="dashboard.api.preferences", title="Preferences API", product="dashboard", api_path="/api/preferences", primary_controls=["preference storage"], local_checks=DASHBOARD_MUTATION_BASE),
        api_surface(surface_id="dashboard.api.feedback", title="Feedback API", product="dashboard", api_path="/api/feedback", primary_controls=["explicit feedback"], local_checks=DASHBOARD_MUTATION_BASE),
        api_surface(surface_id="dashboard.api.feedback-implicit", title="Implicit Feedback API", product="dashboard", api_path="/api/feedback/implicit", primary_controls=["implicit telemetry feedback"], local_checks=DASHBOARD_MUTATION_BASE),
        api_surface(surface_id="dashboard.api.insights-run", title="Insights Run API", product="dashboard", api_path="/api/insights/run", primary_controls=["queue insight analysis"], local_checks=DASHBOARD_MUTATION_BASE),
        api_surface(surface_id="dashboard.api.learning-benchmarks", title="Learning Benchmarks API", product="dashboard", api_path="/api/learning/benchmarks", primary_controls=["queue benchmark run"], local_checks=DASHBOARD_MUTATION_BASE),
        api_surface(surface_id="dashboard.api.push-subscribe", title="Push Subscription API", product="dashboard", api_path="/api/push/subscribe", primary_controls=["subscribe", "unsubscribe"], local_checks=DASHBOARD_MUTATION_BASE + ["projects/dashboard/tests/e2e/browser-integrations.spec.ts"]),
        api_surface(surface_id="dashboard.api.push-send", title="Push Send API", product="dashboard", api_path="/api/push/send", primary_controls=["send operator notification"], local_checks=DASHBOARD_MUTATION_BASE),
        api_surface(surface_id="dashboard.api.tts", title="TTS API", product="dashboard", api_path="/api/tts", primary_controls=["speech synthesis"], local_checks=DASHBOARD_MUTATION_BASE),
        api_surface(surface_id="dashboard.api.comfyui-generate", title="ComfyUI Generate API", product="dashboard", api_path="/api/comfyui/generate", primary_controls=["queue creative generation"], local_checks=DASHBOARD_MUTATION_BASE),
        api_surface(surface_id="dashboard.api.comfyui-history", title="ComfyUI History API", product="dashboard", api_path="/api/comfyui/history", primary_controls=["generation history"], local_checks=DASHBOARD_MUTATION_BASE),
        api_surface(surface_id="dashboard.api.comfyui-queue", title="ComfyUI Queue API", product="dashboard", api_path="/api/comfyui/queue", primary_controls=["queue state"], local_checks=DASHBOARD_MUTATION_BASE),
        api_surface(surface_id="dashboard.api.comfyui-stats", title="ComfyUI Stats API", product="dashboard", api_path="/api/comfyui/stats", primary_controls=["device stats"], local_checks=DASHBOARD_MUTATION_BASE),
        api_surface(surface_id="dashboard.api.workforce-tasks", title="Workforce Tasks API", product="dashboard", api_path="/api/workforce/tasks", primary_controls=["list tasks", "submit task"], local_checks=DASHBOARD_MUTATION_BASE),
        api_surface(surface_id="dashboard.api.workforce-goals", title="Workforce Goals API", product="dashboard", api_path="/api/workforce/goals", primary_controls=["create goal", "delete goal"], local_checks=DASHBOARD_MUTATION_BASE),
        api_surface(surface_id="dashboard.api.workforce-plan", title="Workforce Plan API", product="dashboard", api_path="/api/workforce/plan", primary_controls=["generate work plan"], local_checks=DASHBOARD_MUTATION_BASE),
        api_surface(surface_id="dashboard.api.workforce-redirect", title="Workforce Redirect API", product="dashboard", api_path="/api/workforce/redirect", primary_controls=["redirect work plan"], local_checks=DASHBOARD_MUTATION_BASE),
    ]
)

_extend(
    [
        workflow_surface(surface_id="dashboard.workflow.keyboard-command-palette", title="Dashboard Command Palette Shortcut", product="dashboard", route_path="/", owned_apis=[], primary_controls=["Ctrl/Cmd+K opens and closes the command palette"], local_checks=["projects/dashboard/tests/e2e/browser-integrations.spec.ts"]),
        workflow_surface(surface_id="dashboard.workflow.service-worker-and-push", title="Dashboard Service Worker and Push Lifecycle", product="dashboard", route_path="/preferences", owned_apis=["/api/push/subscribe", "/api/push/send"], primary_controls=["service worker registration", "push enable", "push disable"], local_checks=["projects/dashboard/tests/e2e/browser-integrations.spec.ts"], manual_checklist=["Validate a real browser notification with live VAPID keys before shipping push changes."]),
        workflow_surface(surface_id="dashboard.workflow.chat-handoff", title="Dashboard Chat and Agent Handoff", product="dashboard", route_path="/chat", owned_apis=["/api/chat"], primary_controls=["direct chat on worker", "LiteLLM routed chat", "agent chat with tool activity"], local_checks=["projects/dashboard/tests/e2e/consoles.spec.ts"], live_checks=["scripts/tests/live-dashboard-smoke.py::chat-results"]),
        workflow_surface(surface_id="dashboard.workflow.drawer-return-paths", title="Dashboard Drawer Return Paths", product="dashboard", route_path="/monitoring", owned_apis=["/api/monitoring", "/api/media/overview", "/api/home/overview", "/api/gallery/overview"], primary_controls=["monitoring drawer return", "media drawer return", "home drawer return", "gallery drawer return"], local_checks=["projects/dashboard/tests/e2e/family-flows.spec.ts"], live_checks=["scripts/tests/live-dashboard-smoke.py::drawer-launches"]),
        workflow_surface(surface_id="dashboard.workflow.clipboard-and-export-actions", title="Dashboard Clipboard and Export Actions", product="dashboard", route_path="/chat", owned_apis=[], primary_controls=["copy transcript", "copy endpoints", "export session payloads"], local_checks=["projects/dashboard/tests/e2e/clipboard-exports.spec.ts"]),
    ]
)
