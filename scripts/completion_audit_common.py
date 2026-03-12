#!/usr/bin/env python3
"""Shared helpers for the Athanor completion-audit toolchain."""

from __future__ import annotations

import ast
import html
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_ROOT = REPO_ROOT / "projects" / "dashboard"
DASHBOARD_SRC = DASHBOARD_ROOT / "src"
DASHBOARD_APP = DASHBOARD_SRC / "app"
DASHBOARD_COMPONENTS = DASHBOARD_SRC / "components"
DASHBOARD_FEATURES = DASHBOARD_SRC / "features"
DASHBOARD_HOOKS = DASHBOARD_SRC / "hooks"
AGENTS_ROOT = REPO_ROOT / "projects" / "agents"
AGENTS_SRC = AGENTS_ROOT / "src" / "athanor_agents"
AGENT_SERVER = AGENTS_SRC / "server.py"
ATLAS_COMPLETION_DIR = REPO_ROOT / "docs" / "atlas" / "inventory" / "completion"
REPORTS_DIR = REPO_ROOT / "reports" / "completion-audit"
UI_AUDIT_DIR = REPO_ROOT / "tests" / "ui-audit"

TS_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".mts")
IMPORT_RE = re.compile(r"""from\s+["']([^"']+)["']|import\s+["']([^"']+)["']|import\(\s*["']([^"']+)["']\s*\)""")
ENV_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"process\.env\.([A-Z0-9_]+)"),
    re.compile(r"os\.environ(?:\.get)?\(\s*['\"]([A-Z0-9_]+)['\"]"),
    re.compile(r"os\.getenv\(\s*['\"]([A-Z0-9_]+)['\"]"),
    re.compile(r"AliasChoices\(([^)]*)\)"),
    re.compile(r"validation_alias=AliasChoices\(([^)]*)\)"),
    re.compile(r"-\s+([A-Z0-9_]+)="),
    re.compile(r"\$\{([A-Z0-9_]+)(?::-[^}]*)?\}"),
)
VALID_ENV_NAME_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")
HTTP_METHOD_RE = re.compile(r"export\s+async\s+function\s+(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\b")
ROUTE_HEADING_RE = re.compile(r"""heading:\s*(?:"([^"]+)"|/([^/]+)/i?)""")
ROUTE_TITLE_PROP_RE = re.compile(r"""title:\s*(?:"([^"]+)"|/([^/]+)/i?)""")
JSX_TITLE_RE = re.compile(r'title=\s*"([^"]+)"')
H1_TEXT_RE = re.compile(r"""<h1[^>]*>\s*(.*?)\s*</h1>""", re.DOTALL)
SURFACE_TEST_PATH_RE = re.compile(r"^[A-Za-z0-9_/.\-:]+$")

PARTIAL_UI_BASENAMES = set()
DEPRECATED_UI_BASENAMES = {
    "activity-feed.tsx",
    "auto-refresh.tsx",
    "bottom-nav.tsx",
    "category-overview.tsx",
    "command.tsx",
    "dialog.tsx",
    "generative-ui.ts",
    "graph-summary.tsx",
    "gpu-card.tsx",
    "home-sections.tsx",
    "implicit-feedback-tracker.tsx",
    "pull-to-refresh.tsx",
    "recent-items.tsx",
    "separator.tsx",
    "sidebar-nav.tsx",
    "speech.d.ts",
    "swipe-card.tsx",
    "system-pulse.tsx",
    "tool-call.tsx",
    "use-implicit-feedback.tsx",
    "voice-input.tsx",
    "voice-output.tsx",
}
UNMOUNTED_UI_BASENAMES = {
    "auto-refresh.tsx",
}

ROUTE_PAGE_FILES = {
    "page.tsx",
    "layout.tsx",
    "loading.tsx",
    "error.tsx",
    "global-error.tsx",
    "not-found.tsx",
    "template.tsx",
    "default.tsx",
}
ENTRY_ROOT_FILES = ROUTE_PAGE_FILES | {"route.ts"}

DEPLOYMENT_SERVICE_MATRIX = [
    {
        "serviceId": "dashboard",
        "title": "Command Center dashboard",
        "node": "WORKSHOP",
        "ownerLayer": "project",
        "repoSources": [
            "projects/dashboard/docker-compose.yml",
            "projects/dashboard",
            "ansible/roles/dashboard/templates/docker-compose.yml.j2",
        ],
        "liveEndpoint": "http://192.168.1.225:3001",
        "driftStatus": "aligned",
        "notes": [
            "Project-local dashboard manifests are the strongest source for the UI layer.",
        ],
    },
    {
        "serviceId": "terminal-bridge",
        "title": "Workshop terminal bridge",
        "node": "WORKSHOP",
        "ownerLayer": "project",
        "repoSources": [
            "projects/dashboard",
            "ansible/roles/dashboard/templates/docker-compose.yml.j2",
        ],
        "liveEndpoint": "http://192.168.1.225:3100",
        "driftStatus": "aligned",
        "notes": [
            "Owned by the dashboard deployment surface on Workshop.",
        ],
    },
    {
        "serviceId": "agent-server",
        "title": "Athanor agent server",
        "node": "FOUNDRY",
        "ownerLayer": "project",
        "repoSources": [
            "projects/agents/docker-compose.yml",
            "projects/agents/src/athanor_agents",
            "ansible/roles/agents/templates/docker-compose.yml.j2",
        ],
        "liveEndpoint": "http://192.168.1.244:9000/health",
        "driftStatus": "aligned",
        "notes": [
            "Project-local agent manifests and code own runtime behavior, and the live Foundry deployment now matches the repo-backed coder-era compose.",
        ],
    },
    {
        "serviceId": "litellm",
        "title": "LiteLLM routing layer",
        "node": "VAULT",
        "ownerLayer": "ansible",
        "repoSources": [
            "ansible/roles/vault-litellm/templates/litellm_config.yaml.j2",
            "ansible/roles/vault-litellm",
        ],
        "liveEndpoint": "http://192.168.1.203:4000/health",
        "driftStatus": "aligned",
        "notes": [
            "VAULT LiteLLM was reloaded from the repo-backed coder-era routing template and now exposes the subscription provider portfolio through the managed config.",
        ],
    },
    {
        "serviceId": "monitoring",
        "title": "Prometheus and Grafana",
        "node": "VAULT",
        "ownerLayer": "ansible",
        "repoSources": [
            "ansible/roles/vault-monitoring",
            "ansible/roles/prometheus",
            "ansible/roles/grafana",
        ],
        "liveEndpoint": "http://192.168.1.203:3000",
        "driftStatus": "aligned",
        "notes": [
            "VAULT Prometheus, alert rules, and blackbox exporter were converged onto the Athanor monitoring model under /mnt/appdatacache/appdata.",
        ],
    },
    {
        "serviceId": "qdrant",
        "title": "Canonical Qdrant store",
        "node": "FOUNDRY",
        "ownerLayer": "ansible",
        "repoSources": [
            "ansible/roles/qdrant",
            "docs/SERVICES.md",
        ],
        "liveEndpoint": "http://192.168.1.244:6333/collections",
        "driftStatus": "aligned",
        "notes": [
            "Canonical vector store for the live runtime.",
        ],
    },
    {
        "serviceId": "neo4j",
        "title": "Neo4j knowledge graph",
        "node": "VAULT",
        "ownerLayer": "ansible",
        "repoSources": [
            "ansible/roles/vault-neo4j",
            "docs/SERVICES.md",
        ],
        "liveEndpoint": "http://192.168.1.203:7474",
        "driftStatus": "aligned",
        "notes": [
            "Knowledge graph runtime on VAULT.",
        ],
    },
    {
        "serviceId": "redis",
        "title": "Redis control plane",
        "node": "VAULT",
        "ownerLayer": "ansible",
        "repoSources": [
            "ansible/roles/redis",
            "docs/SERVICES.md",
        ],
        "liveEndpoint": "redis://192.168.1.203:6379/0",
        "driftStatus": "aligned",
        "notes": [
            "Backs task queue, workspace, and scheduler state.",
        ],
    },
    {
        "serviceId": "workshop-worker",
        "title": "Workshop worker vLLM",
        "node": "WORKSHOP",
        "ownerLayer": "services",
        "repoSources": [
            "services/node2",
            "ansible/roles/vllm-worker",
        ],
        "liveEndpoint": "http://192.168.1.225:8000/v1/models",
        "driftStatus": "aligned",
        "notes": [
            "Service-level manifests currently match live better than some Ansible roles.",
        ],
    },
    {
        "serviceId": "foundry-coordinator",
        "title": "Foundry reasoning vLLM",
        "node": "FOUNDRY",
        "ownerLayer": "services",
        "repoSources": [
            "services/node1",
            "ansible/roles/vllm",
        ],
        "liveEndpoint": "http://192.168.1.244:8000/v1/models",
        "driftStatus": "aligned",
        "notes": [
            "Foundry coordinator runtime is represented best by node service manifests.",
        ],
    },
    {
        "serviceId": "comfyui",
        "title": "Workshop ComfyUI",
        "node": "WORKSHOP",
        "ownerLayer": "services",
        "repoSources": [
            "services/node2",
            "docs/SERVICES.md",
        ],
        "liveEndpoint": "http://192.168.1.225:8188/system_stats",
        "driftStatus": "aligned",
        "notes": [
            "Creative generation backend consumed by gallery/media surfaces.",
        ],
    },
    {
        "serviceId": "subscription-control",
        "title": "Subscription control layer",
        "node": "FOUNDRY",
        "ownerLayer": "project",
        "repoSources": [
            "projects/agents/src/athanor_agents/subscriptions.py",
            "projects/agents/config/subscription-routing-policy.yaml",
            "ansible/roles/agents/templates/docker-compose.yml.j2",
        ],
        "liveEndpoint": "http://192.168.1.244:9000/v1/subscriptions/policy",
        "driftStatus": "aligned",
        "notes": [
            "Lives inside the agent server deployment boundary.",
        ],
    },
]


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_json(path: Path, payload: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "root"


def humanize_slug(value: str) -> str:
    return value.replace("-", " ").replace("_", " ").title()


def normalize_dynamic_segment(segment: str) -> str:
    if segment.startswith("[[...") and segment.endswith("]]"):
        return f":{segment[5:-2]}*"
    if segment.startswith("[...") and segment.endswith("]"):
        return f":{segment[4:-1]}*"
    if segment.startswith("[") and segment.endswith("]"):
        return f":{segment[1:-1]}"
    return segment


def app_dir_to_route_path(directory: Path, *, include_api: bool = False) -> str | None:
    relative = directory.relative_to(DASHBOARD_APP)
    parts: list[str] = []
    for segment in relative.parts:
        if segment == "api" and not include_api:
            return None
        if segment == "api" and include_api:
            parts.append("api")
            continue
        if segment.startswith("(") and segment.endswith(")"):
            continue
        if segment.startswith("@"):
            continue
        parts.append(normalize_dynamic_segment(segment))

    if not parts:
        return "/"
    return "/" + "/".join(parts)


def api_dir_to_api_path(directory: Path) -> str:
    relative = directory.relative_to(DASHBOARD_APP / "api")
    if not relative.parts:
        return "/api"
    return "/api/" + "/".join(normalize_dynamic_segment(part) for part in relative.parts)


@lru_cache(maxsize=1)
def load_navigation() -> dict[str, dict[str, Any]]:
    text = read_text(DASHBOARD_SRC / "lib" / "navigation.ts")
    routes_match = re.search(r"export const ROUTES: RouteDefinition\[] = \[(.*?)\];", text, re.DOTALL)
    if routes_match is None:
        return {}

    block = routes_match.group(1)
    entries: list[dict[str, Any]] = []
    current = []
    depth = 0
    for char in block:
        if char == "{":
            depth += 1
        if depth > 0:
            current.append(char)
        if char == "}":
            depth -= 1
            if depth == 0 and current:
                entries.append(_parse_route_object("".join(current)))
                current = []

    return {
        entry["href"]: entry
        for entry in entries
        if entry.get("href")
    }


def _parse_route_object(block: str) -> dict[str, Any]:
    def extract(pattern: str, default: Any = None) -> Any:
        match = re.search(pattern, block, re.DOTALL)
        return match.group(1) if match else default

    def extract_bool(pattern: str) -> bool | None:
        match = re.search(pattern, block)
        if not match:
            return None
        return match.group(1) == "true"

    return {
        "href": extract(r'href:\s*"([^"]+)"'),
        "label": extract(r'label:\s*"([^"]+)"'),
        "shortLabel": extract(r'shortLabel:\s*"([^"]+)"'),
        "description": extract(r'description:\s*"([^"]+)"'),
        "family": extract(r'family:\s*"([^"]+)"'),
        "primary": extract_bool(r"primary:\s*(true|false)"),
        "mobile": extract_bool(r"mobile:\s*(true|false)"),
    }


@lru_cache(maxsize=1)
def load_surface_registry() -> dict[str, dict[str, Any]]:
    registry_path = UI_AUDIT_DIR / "surface-registry.json"
    if not registry_path.exists():
        return {"routes": {}, "apis": {}}
    payload = json.loads(read_text(registry_path))
    routes: dict[str, dict[str, Any]] = {}
    apis: dict[str, dict[str, Any]] = {}
    for surface in payload.get("surfaces", []):
        route_path = surface.get("routePath")
        api_path = surface.get("apiPath")
        if route_path:
            routes.setdefault(route_path, surface)
        if api_path:
            apis.setdefault(api_path, surface)
    return {"routes": routes, "apis": apis}


def normalize_api_path(path: str) -> str:
    parts = []
    for segment in path.strip().split("/"):
        if not segment:
            continue
        if segment.startswith(":"):
            parts.append(segment)
        else:
            parts.append(normalize_dynamic_segment(segment))
    return "/" + "/".join(parts)


def file_to_id(prefix: str, file_path: Path) -> str:
    relative = file_path.relative_to(REPO_ROOT).with_suffix("")
    return prefix + "." + slugify(relative.as_posix().replace("/", "-"))


def extract_imports(path: Path) -> list[str]:
    text = read_text(path)
    imports: list[str] = []
    for match in IMPORT_RE.finditer(text):
        spec = match.group(1) or match.group(2) or match.group(3)
        if spec:
            imports.append(spec)
    return imports


def resolve_import(source_file: Path, spec: str) -> Path | None:
    if spec.startswith("@/"):
        base = DASHBOARD_SRC / spec[2:]
    elif spec.startswith("."):
        base = (source_file.parent / spec).resolve()
    else:
        return None

    candidates = [base]
    if base.suffix:
        candidates.append(base.with_suffix(""))
    for extension in TS_EXTENSIONS:
        candidates.append(Path(f"{base}{extension}"))
        candidates.append(base / f"index{extension}")
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def list_dashboard_source_files() -> list[Path]:
    return [
        path
        for path in DASHBOARD_SRC.rglob("*")
        if path.is_file() and path.suffix in TS_EXTENSIONS
    ]


def list_dashboard_ui_files() -> list[Path]:
    return [
        path
        for path in DASHBOARD_SRC.rglob("*")
        if path.is_file()
        and path.suffix in TS_EXTENSIONS
        and "app\\api" not in str(path)
        and "/app/api/" not in path.as_posix()
        and ".stories." not in path.name
        and ".test." not in path.name
    ]


def discover_page_roots() -> list[Path]:
    roots: list[Path] = []
    for path in DASHBOARD_APP.rglob("*"):
        if not path.is_file():
            continue
        if path.name not in ENTRY_ROOT_FILES:
            continue
        roots.append(path)
    return sorted(roots)


def parse_http_methods(path: Path) -> list[str]:
    methods = sorted(set(HTTP_METHOD_RE.findall(read_text(path))))
    return methods or ["GET"]


def detect_response_mode(path: Path) -> str:
    text = read_text(path)
    if "text/event-stream" in text:
        return "sse"
    if "application/octet-stream" in text or "audio/mpeg" in text:
        return "binary"
    if "NextResponse.json" in text or "Response.json" in text:
        return "json"
    return "unknown"


def extract_heading_from_text(text: str) -> str | None:
    for pattern in (ROUTE_HEADING_RE, ROUTE_TITLE_PROP_RE, JSX_TITLE_RE):
        match = pattern.search(text)
        if not match:
            continue
        groups = match.groups()
        value = next((group for group in groups if group), None)
        if value:
            return html.unescape(value.strip())

    h1_match = H1_TEXT_RE.search(text)
    if not h1_match:
        return None

    raw = h1_match.group(1)
    normalized = re.sub(r"<[^>]+>", " ", raw)
    normalized = normalized.replace("{", " ").replace("}", " ")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if normalized:
        return html.unescape(normalized)
    return None


def scan_route_headings() -> dict[str, str]:
    headings: dict[str, str] = {}
    for page_file in DASHBOARD_APP.rglob("page.tsx"):
        if "/app/api/" in page_file.as_posix():
            continue
        route_path = app_dir_to_route_path(page_file.parent)
        if route_path is None:
            continue
        navigation = load_navigation().get(route_path, {})
        candidate_files = [page_file]
        for spec in extract_imports(page_file):
            resolved = resolve_import(page_file, spec)
            if resolved is not None:
                candidate_files.append(resolved)
        seen: set[Path] = set()
        for candidate in candidate_files:
            if candidate in seen:
                continue
            seen.add(candidate)
            title = extract_heading_from_text(read_text(candidate))
            if title:
                headings[route_path] = title
                break
        if route_path in headings:
            continue
        title = navigation.get("label")
        if isinstance(title, str) and title:
            headings[route_path] = title
        else:
            headings[route_path] = humanize_slug(page_file.parent.name)
    headings["/"] = headings.get("/", "Command Center")
    return headings


def build_dashboard_import_graph() -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    graph: dict[str, set[str]] = {}
    reverse: dict[str, set[str]] = {}
    for file_path in list_dashboard_source_files():
        source = file_path.relative_to(REPO_ROOT).as_posix()
        graph.setdefault(source, set())
        for spec in extract_imports(file_path):
            resolved = resolve_import(file_path, spec)
            if resolved is None:
                continue
            target = resolved.relative_to(REPO_ROOT).as_posix()
            graph[source].add(target)
            reverse.setdefault(target, set()).add(source)
    return graph, reverse


def collect_reachable_files(graph: dict[str, set[str]], roots: list[Path]) -> dict[str, set[str]]:
    root_map: dict[str, set[str]] = {}
    for root in roots:
        root_key = root.relative_to(REPO_ROOT).as_posix()
        queue = [root_key]
        seen = {root_key}
        while queue:
            current = queue.pop(0)
            root_map.setdefault(current, set()).add(root_key)
            for target in graph.get(current, set()):
                if target in seen:
                    continue
                seen.add(target)
                queue.append(target)
                root_map.setdefault(target, set()).add(root_key)
    return root_map


def safe_json_load(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(read_text(path))


def extract_env_names(text: str) -> set[str]:
    envs: set[str] = set()
    for pattern in ENV_PATTERNS:
        for match in pattern.finditer(text):
            if pattern.pattern.startswith("validation_alias"):
                args = match.group(1)
                envs.update(
                    name
                    for name in re.findall(r'["\']([A-Z0-9_]+)["\']', args)
                    if VALID_ENV_NAME_RE.match(name)
                )
            elif "AliasChoices" in pattern.pattern:
                args = match.group(1)
                envs.update(
                    name
                    for name in re.findall(r'["\']([A-Z0-9_]+)["\']', args)
                    if VALID_ENV_NAME_RE.match(name)
                )
            else:
                candidate = match.group(1)
                if VALID_ENV_NAME_RE.match(candidate):
                    envs.add(candidate)
    return envs


def parse_agent_metadata() -> dict[str, Any]:
    tree = ast.parse(read_text(AGENT_SERVER))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "AGENT_METADATA":
                    return ast.literal_eval(node.value)
    return {}


def classify_mount_status(file_path: Path, reachable_roots: set[str]) -> str:
    basename = file_path.name
    if basename in DEPRECATED_UI_BASENAMES:
        return "deprecated"
    if "/components/gen-ui/" in file_path.as_posix() and basename != "feedback-buttons.tsx":
        return "deprecated"
    if basename in UNMOUNTED_UI_BASENAMES:
        return "unmounted"
    if basename in PARTIAL_UI_BASENAMES:
        return "partial"
    if not reachable_roots:
        return "unmounted"
    return "mounted"


def match_surface_api(surface_api: str, api_path: str) -> bool:
    if "[" in surface_api and "]" in surface_api:
        surface_api = normalize_api_path(surface_api)
    if surface_api == api_path:
        return True
    if "*" in surface_api:
        pattern = "^" + re.escape(surface_api).replace(r"\*", r".*") + "$"
        return re.match(pattern, api_path) is not None
    if ":" not in surface_api:
        return False
    pattern = re.escape(surface_api)
    pattern = pattern.replace(r"\:taskId", r"[^/]+")
    pattern = pattern.replace(r"\:goalId", r"[^/]+")
    pattern = pattern.replace(r"\:notificationId", r"[^/]+")
    pattern = pattern.replace(r"\:itemId", r"[^/]+")
    pattern = pattern.replace(r"\:conventionId", r"[^/]+")
    pattern = "^" + pattern + "$"
    return re.match(pattern, api_path) is not None


def load_runtime_inventory() -> dict[str, dict[str, Any]]:
    inventory = safe_json_load(REPO_ROOT / "docs" / "atlas" / "inventory" / "runtime-inventory.json", [])
    return {item["id"]: item for item in inventory}
