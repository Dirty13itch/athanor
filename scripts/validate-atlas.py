#!/usr/bin/env python3
"""Validate the Athanor atlas docs and inventory layer.

Checks performed:
- required atlas docs and inventory files exist
- inventory JSON parses and follows the shared atlas record schema
- record ids are unique and internal dependency references resolve
- repo_source paths and globs resolve inside the repo
- UI inventory route coverage matches dashboard navigation.ts exactly
- UI atlas route-family and route tables match navigation.ts exactly
- shared console families are present with the expected grouped routes
- dashboard API inventory covers every Next.js API route handler
- dashboard API families are consumed by at least one UI inventory item
- runtime inventory covers every agent in AGENT_METADATA
- required topology, runtime, and UI cross-cutting ids exist
- older map docs carry atlas-first notes

Usage:
    python scripts/validate-atlas.py
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
ATLAS_DIR = REPO_ROOT / "docs" / "atlas"
INVENTORY_DIR = ATLAS_DIR / "inventory"

REQUIRED_ATLAS_DOCS = [
    ATLAS_DIR / "README.md",
    ATLAS_DIR / "TOPOLOGY_ATLAS.md",
    ATLAS_DIR / "RUNTIME_ATLAS.md",
    ATLAS_DIR / "UI_ATLAS.md",
    ATLAS_DIR / "API_ATLAS.md",
    ATLAS_DIR / "SOURCE_RECONCILIATION.md",
]

LEGACY_MAP_DOCS = [
    REPO_ROOT / "docs" / "planning" / "ATHANOR-MAP.md",
    REPO_ROOT / "docs" / "planning" / "ATHANOR-MAP-ADDENDUM.md",
    REPO_ROOT / "docs" / "hardware" / "ATHANOR-SYSTEM-MAP.md",
    REPO_ROOT / "docs" / "hardware" / "COMPLETE-SYSTEM-BREAKDOWN.md",
]

INVENTORY_FILES = {
    "topology": INVENTORY_DIR / "topology-inventory.json",
    "runtime": INVENTORY_DIR / "runtime-inventory.json",
    "ui": INVENTORY_DIR / "ui-inventory.json",
    "api": INVENTORY_DIR / "api-inventory.json",
}

SCHEMA_FILE = INVENTORY_DIR / "atlas-record.schema.json"
NAVIGATION_FILE = REPO_ROOT / "projects" / "dashboard" / "src" / "lib" / "navigation.ts"
UI_ATLAS_FILE = ATLAS_DIR / "UI_ATLAS.md"
SERVER_FILE = REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents" / "server.py"
DASHBOARD_API_DIR = REPO_ROOT / "projects" / "dashboard" / "src" / "app" / "api"

ROUTE_FAMILY_SECTION = "## Route Families"
SHARED_CONSOLE_SECTION = "## Shared Console Families"
ROUTE_SECTION_EXCLUSIONS = {ROUTE_FAMILY_SECTION, SHARED_CONSOLE_SECTION}
INTERNAL_ID_RE = re.compile(r"^(topology|runtime|ui|api)\.")
GLOB_CHARS = set("*?")

EXPECTED_SHARED_CONSOLES = {
    "HistoryConsole": {"/activity", "/conversations", "/outputs"},
    "IntelligenceConsole": {"/insights", "/learning", "/review"},
    "MemoryConsole": {"/preferences", "/personal-data"},
    "Workforce consoles": {"/tasks", "/goals", "/notifications", "/workspace", "/workplanner"},
}

REQUIRED_TOPOLOGY_IDS = {
    "topology.node.foundry",
    "topology.node.workshop",
    "topology.node.vault",
    "topology.node.dev",
    "topology.service.dashboard",
    "topology.service.agent-server",
    "topology.service.litellm",
    "topology.service.prometheus-grafana",
    "topology.store.qdrant",
    "topology.store.neo4j",
    "topology.store.redis",
    "topology.model.reasoning",
    "topology.model.worker",
    "topology.model.embedding",
    "topology.model.cloud",
    "topology.deployment.sources",
}

REQUIRED_RUNTIME_IDS = {
    "runtime.subsystem.task-engine",
    "runtime.subsystem.workspace",
    "runtime.subsystem.goals-workplan",
    "runtime.subsystem.notifications-escalation",
    "runtime.subsystem.patterns-learning",
    "runtime.subsystem.subscriptions",
}

REQUIRED_UI_IDS = {
    "ui.system.app-shell",
    "ui.system.command-palette",
    "ui.system.url-state",
    "ui.system.local-state",
    "ui.system.lens",
    "ui.system.pwa",
    "ui.system.terminal-bridge",
}

REQUIRED_FIELDS = [
    "id",
    "layer",
    "title",
    "kind",
    "owner",
    "source_of_truth",
    "status_tag",
    "repo_source",
    "runtime_source",
    "depends_on",
    "backed_by",
    "entrypoints",
    "notes",
]

VALID_LAYERS = {"topology", "runtime", "ui", "api"}
VALID_STATUS_TAGS = {"live", "implemented_not_live", "planned", "deprecated", "legacy"}


class ValidationError(Exception):
    """Raised when a validation step fails."""


def fail(message: str) -> None:
    raise ValidationError(message)


def repo_rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{repo_rel(path)} is not valid JSON: {exc}")


def ensure_files_exist(paths: list[Path], label: str) -> None:
    missing = [repo_rel(path) for path in paths if not path.exists()]
    if missing:
        fail(f"Missing {label}: {', '.join(missing)}")


def validate_record(record: dict, expected_layer: str, record_index: int, source_file: Path) -> None:
    prefix = f"{repo_rel(source_file)}[{record_index}]"
    for field in REQUIRED_FIELDS:
        if field not in record:
            fail(f"{prefix} is missing required field '{field}'")

    for field in ("id", "title", "kind", "owner", "source_of_truth"):
        value = record[field]
        if not isinstance(value, str) or not value.strip():
            fail(f"{prefix}.{field} must be a non-empty string")

    if record["layer"] != expected_layer:
        fail(f"{prefix}.layer must be '{expected_layer}', found '{record['layer']}'")
    if record["layer"] not in VALID_LAYERS:
        fail(f"{prefix}.layer has invalid value '{record['layer']}'")
    if record["status_tag"] not in VALID_STATUS_TAGS:
        fail(f"{prefix}.status_tag has invalid value '{record['status_tag']}'")

    for field in ("repo_source", "runtime_source", "depends_on", "backed_by", "entrypoints", "notes"):
        value = record[field]
        if not isinstance(value, list):
            fail(f"{prefix}.{field} must be an array")
        if any(not isinstance(item, str) or not item.strip() for item in value):
            fail(f"{prefix}.{field} must contain only non-empty strings")


def resolve_repo_source(path_spec: str) -> list[Path]:
    if any(char in GLOB_CHARS for char in path_spec):
        return sorted(REPO_ROOT.glob(path_spec))
    candidate = REPO_ROOT / Path(path_spec)
    return [candidate] if candidate.exists() else []


def parse_navigation() -> tuple[dict[str, set[str]], set[str]]:
    text = NAVIGATION_FILE.read_text(encoding="utf-8")
    families_match = re.search(
        r"export const ROUTE_FAMILIES: RouteFamilyDefinition\[] = \[(.*?)\];",
        text,
        re.DOTALL,
    )
    routes_match = re.search(
        r"export const ROUTES: RouteDefinition\[] = \[(.*?)\];",
        text,
        re.DOTALL,
    )
    if families_match is None or routes_match is None:
        fail("Could not parse projects/dashboard/src/lib/navigation.ts")

    family_ids = re.findall(r'id:\s*"([^"]+)"', families_match.group(1))
    route_pairs = re.findall(r'href:\s*"([^"]+)".*?family:\s*"([^"]+)"', routes_match.group(1), re.DOTALL)
    if not family_ids or not route_pairs:
        fail("navigation.ts did not yield any route families or routes")

    family_map = {family_id: set() for family_id in family_ids}
    for href, family_id in route_pairs:
        family_map.setdefault(family_id, set()).add(href)

    route_set = {href for href, _family in route_pairs}
    return family_map, route_set


def split_markdown_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = "__root__"
    sections[current] = []
    for line in text.splitlines():
        if line.startswith("## "):
            current = line.strip()
            sections[current] = []
        sections[current].append(line)
    return sections


def first_table_rows(section_lines: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    in_table = False
    for line in section_lines:
        if line.startswith("|"):
            in_table = True
            stripped = line.strip().strip("|")
            if not stripped:
                continue
            columns = [part.strip() for part in stripped.split("|")]
            if all(set(column) <= {"-", ":", " "} for column in columns):
                continue
            rows.append(columns)
        elif in_table:
            break
    return rows


def extract_markdown_paths(cell: str) -> set[str]:
    code_paths = re.findall(r"`([^`]+)`", cell)
    if code_paths:
        return {path.strip() for path in code_paths if path.strip()}
    return {part.strip() for part in cell.split(",") if part.strip()}


def parse_ui_atlas(text: str) -> tuple[dict[str, set[str]], set[str], dict[str, set[str]]]:
    sections = split_markdown_sections(text)

    if ROUTE_FAMILY_SECTION not in sections:
        fail("UI_ATLAS.md is missing the '## Route Families' section")
    family_rows = first_table_rows(sections[ROUTE_FAMILY_SECTION])
    if len(family_rows) < 2:
        fail("UI_ATLAS.md route family table is empty")
    family_map: dict[str, set[str]] = {}
    for row in family_rows[1:]:
        if len(row) < 5:
            fail("UI_ATLAS.md route family table has malformed rows")
        family_id = row[0].strip("`")
        family_map[family_id] = extract_markdown_paths(row[2])

    route_sections = [
        title
        for title in sections
        if title.startswith("## ")
        and title.endswith("Routes")
        and title not in ROUTE_SECTION_EXCLUSIONS
    ]
    route_set: set[str] = set()
    duplicates: set[str] = set()
    for title in route_sections:
        table_rows = first_table_rows(sections[title])
        if len(table_rows) < 2:
            fail(f"UI_ATLAS.md section '{title}' does not have a route table")
        for row in table_rows[1:]:
            if not row:
                continue
            route_cell = row[0]
            route_matches = extract_markdown_paths(route_cell)
            if len(route_matches) != 1:
                fail(f"UI_ATLAS.md section '{title}' has malformed route cell '{route_cell}'")
            route = next(iter(route_matches))
            if route in route_set:
                duplicates.add(route)
            route_set.add(route)

    if duplicates:
        fail(f"UI_ATLAS.md route tables contain duplicates: {', '.join(sorted(duplicates))}")

    if SHARED_CONSOLE_SECTION not in sections:
        fail("UI_ATLAS.md is missing the '## Shared Console Families' section")
    shared_rows = first_table_rows(sections[SHARED_CONSOLE_SECTION])
    if len(shared_rows) < 2:
        fail("UI_ATLAS.md shared console family table is empty")
    shared_console_map: dict[str, set[str]] = {}
    for row in shared_rows[1:]:
        if len(row) < 4:
            fail("UI_ATLAS.md shared console table has malformed rows")
        shared_console_map[row[0].strip("`")] = extract_markdown_paths(row[1])

    return family_map, route_set, shared_console_map


def parse_agent_metadata_keys() -> set[str]:
    tree = ast.parse(SERVER_FILE.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "AGENT_METADATA":
                    metadata = ast.literal_eval(node.value)
                    return set(metadata.keys())
    fail("Could not parse AGENT_METADATA from server.py")


def collect_inventory() -> tuple[dict[str, list[dict]], dict[str, dict], dict]:
    schema = load_json(SCHEMA_FILE)
    inventories: dict[str, list[dict]] = {}
    id_map: dict[str, dict] = {}

    for layer, path in INVENTORY_FILES.items():
        records = load_json(path)
        if not isinstance(records, list):
            fail(f"{repo_rel(path)} must contain a JSON array")
        inventories[layer] = records
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                fail(f"{repo_rel(path)}[{index}] must be a JSON object")
            validate_record(record, layer, index, path)
            record_id = record["id"]
            if record_id in id_map:
                fail(f"Duplicate atlas id '{record_id}' found in multiple inventory files")
            id_map[record_id] = record

    return inventories, id_map, schema


def validate_schema_contract(schema: dict) -> None:
    required = schema.get("required", [])
    if required != REQUIRED_FIELDS:
        fail("atlas-record.schema.json required fields drifted from validator expectations")
    properties = schema.get("properties", {})
    for field in REQUIRED_FIELDS:
        if field not in properties:
            fail(f"atlas-record.schema.json is missing property definition for '{field}'")


def validate_repo_sources(inventories: dict[str, list[dict]]) -> None:
    missing: list[str] = []
    for layer, records in inventories.items():
        for record in records:
            for path_spec in record["repo_source"]:
                resolved = resolve_repo_source(path_spec)
                if not resolved:
                    missing.append(f"{layer}:{record['id']} -> {path_spec}")
    if missing:
        fail("Unresolved repo_source paths:\n- " + "\n- ".join(sorted(missing)))


def validate_internal_references(id_map: dict[str, dict]) -> None:
    missing: list[str] = []
    for record_id, record in id_map.items():
        for dep in record["depends_on"]:
            if INTERNAL_ID_RE.match(dep) and dep not in id_map:
                missing.append(f"{record_id} -> {dep}")
    if missing:
        fail("Unresolved internal depends_on references:\n- " + "\n- ".join(sorted(missing)))


def validate_ui_inventory_routes(ui_records: list[dict], nav_routes: set[str]) -> None:
    inventory_routes = {
        entrypoint
        for record in ui_records
        if record["kind"] == "route"
        for entrypoint in record["entrypoints"]
        if entrypoint.startswith("/")
    }
    missing = sorted(nav_routes - inventory_routes)
    extra = sorted(inventory_routes - nav_routes)
    if missing or extra:
        lines = []
        if missing:
            lines.append("missing in ui inventory: " + ", ".join(missing))
        if extra:
            lines.append("extra in ui inventory: " + ", ".join(extra))
        fail("UI inventory route coverage does not match navigation.ts:\n- " + "\n- ".join(lines))


def validate_ui_families(
    ui_family_map: dict[str, set[str]],
    ui_routes: set[str],
    shared_consoles: dict[str, set[str]],
    nav_family_map: dict[str, set[str]],
    nav_routes: set[str],
) -> None:
    if ui_family_map != nav_family_map:
        issues = []
        for family_id in sorted(set(ui_family_map) | set(nav_family_map)):
            expected = nav_family_map.get(family_id, set())
            actual = ui_family_map.get(family_id, set())
            if expected != actual:
                issues.append(f"{family_id}: expected {sorted(expected)}, found {sorted(actual)}")
        fail("UI_ATLAS.md route family table drifted from navigation.ts:\n- " + "\n- ".join(issues))

    if ui_routes != nav_routes:
        missing = sorted(nav_routes - ui_routes)
        extra = sorted(ui_routes - nav_routes)
        issues = []
        if missing:
            issues.append("missing in UI_ATLAS.md route tables: " + ", ".join(missing))
        if extra:
            issues.append("extra in UI_ATLAS.md route tables: " + ", ".join(extra))
        fail("UI_ATLAS.md route tables do not cover navigation.ts exactly:\n- " + "\n- ".join(issues))

    missing_shared = [
        name for name in EXPECTED_SHARED_CONSOLES if name not in shared_consoles
    ]
    if missing_shared:
        fail("UI_ATLAS.md is missing shared console rows: " + ", ".join(sorted(missing_shared)))
    for name, expected_routes in EXPECTED_SHARED_CONSOLES.items():
        actual_routes = shared_consoles[name]
        if actual_routes != expected_routes:
            fail(
                f"UI_ATLAS.md shared console '{name}' routes drifted: "
                f"expected {sorted(expected_routes)}, found {sorted(actual_routes)}"
            )


def validate_dashboard_api_coverage(api_records: list[dict], ui_records: list[dict]) -> None:
    actual_route_files = {
        repo_rel(path) for path in DASHBOARD_API_DIR.rglob("route.ts")
    }
    covered_route_files: set[str] = set()
    dashboard_family_ids: set[str] = set()

    for record in api_records:
        if record["id"].startswith("api.family.dashboard."):
            dashboard_family_ids.add(record["id"])
        for path_spec in record["repo_source"]:
            for path in resolve_repo_source(path_spec):
                if path.is_file() and path.name == "route.ts":
                    rel = repo_rel(path)
                    if rel.startswith("projects/dashboard/src/app/api/"):
                        covered_route_files.add(rel)

    missing = sorted(actual_route_files - covered_route_files)
    extra = sorted(covered_route_files - actual_route_files)
    if missing or extra:
        issues = []
        if missing:
            issues.append("missing dashboard API routes: " + ", ".join(missing))
        if extra:
            issues.append("extra dashboard API route refs in inventory: " + ", ".join(extra))
        fail("API inventory dashboard route coverage mismatch:\n- " + "\n- ".join(issues))

    family_consumers: dict[str, set[str]] = {family_id: set() for family_id in dashboard_family_ids}
    for record in ui_records:
        for dep in record["depends_on"]:
            if dep in family_consumers:
                family_consumers[dep].add(record["id"])
    unconsumed = sorted(family_id for family_id, consumers in family_consumers.items() if not consumers)
    if unconsumed:
        fail("Dashboard API families are not consumed by any UI inventory item: " + ", ".join(unconsumed))


def validate_runtime_and_topology(
    runtime_records: list[dict],
    topology_records: list[dict],
    ui_records: list[dict],
) -> None:
    runtime_ids = {record["id"] for record in runtime_records}
    topology_ids = {record["id"] for record in topology_records}
    ui_ids = {record["id"] for record in ui_records}

    missing_topology = sorted(REQUIRED_TOPOLOGY_IDS - topology_ids)
    missing_runtime = sorted(REQUIRED_RUNTIME_IDS - runtime_ids)
    missing_ui = sorted(REQUIRED_UI_IDS - ui_ids)

    if missing_topology:
        fail("Topology inventory is missing required ids: " + ", ".join(missing_topology))
    if missing_runtime:
        fail("Runtime inventory is missing required ids: " + ", ".join(missing_runtime))
    if missing_ui:
        fail("UI inventory is missing required cross-cutting ids: " + ", ".join(missing_ui))

    agent_keys = parse_agent_metadata_keys()
    expected_agent_ids = {f"runtime.agent.{name}" for name in agent_keys}
    missing_agents = sorted(expected_agent_ids - runtime_ids)
    extra_agents = sorted(
        runtime_id for runtime_id in runtime_ids if runtime_id.startswith("runtime.agent.") and runtime_id not in expected_agent_ids
    )
    if missing_agents or extra_agents:
        issues = []
        if missing_agents:
            issues.append("missing runtime agents: " + ", ".join(missing_agents))
        if extra_agents:
            issues.append("extra runtime agents: " + ", ".join(extra_agents))
        fail("Runtime inventory agent coverage mismatch:\n- " + "\n- ".join(issues))


def validate_legacy_docs() -> None:
    missing_note = []
    for path in LEGACY_MAP_DOCS:
        text = path.read_text(encoding="utf-8")
        if "Atlas note:" not in text:
            missing_note.append(repo_rel(path))
    if missing_note:
        fail("Legacy map docs are missing atlas notes: " + ", ".join(missing_note))


def print_ok(message: str) -> None:
    print(f"OK  {message}")


def main() -> int:
    try:
        ensure_files_exist(REQUIRED_ATLAS_DOCS, "atlas docs")
        ensure_files_exist(list(INVENTORY_FILES.values()) + [SCHEMA_FILE, NAVIGATION_FILE, UI_ATLAS_FILE, SERVER_FILE], "atlas inputs")
        print_ok(f"required atlas docs and inputs present ({len(REQUIRED_ATLAS_DOCS)} atlas docs)")

        inventories, id_map, schema = collect_inventory()
        validate_schema_contract(schema)
        total_records = sum(len(records) for records in inventories.values())
        print_ok(f"inventory JSON and schema validated ({total_records} records)")

        validate_internal_references(id_map)
        print_ok("internal depends_on references resolve")

        validate_repo_sources(inventories)
        print_ok("repo_source paths and globs resolve")

        nav_family_map, nav_routes = parse_navigation()
        ui_text = UI_ATLAS_FILE.read_text(encoding="utf-8")
        ui_family_map, ui_routes, shared_consoles = parse_ui_atlas(ui_text)
        validate_ui_inventory_routes(inventories["ui"], nav_routes)
        print_ok(f"UI inventory route coverage matches navigation.ts ({len(nav_routes)} routes)")

        validate_ui_families(ui_family_map, ui_routes, shared_consoles, nav_family_map, nav_routes)
        print_ok(f"UI_ATLAS.md route families and route tables match navigation.ts ({len(nav_family_map)} families)")
        print_ok(f"UI_ATLAS.md shared console families validated ({len(EXPECTED_SHARED_CONSOLES)} groups)")

        validate_dashboard_api_coverage(inventories["api"], inventories["ui"])
        dashboard_api_count = len(list(DASHBOARD_API_DIR.rglob('route.ts')))
        print_ok(f"dashboard API inventory covers all Next.js route handlers ({dashboard_api_count} routes)")

        validate_runtime_and_topology(inventories["runtime"], inventories["topology"], inventories["ui"])
        print_ok("runtime agent coverage and required topology/runtime/UI ids validated")

        validate_legacy_docs()
        print_ok(f"legacy map docs point back to the atlas ({len(LEGACY_MAP_DOCS)} docs)")

        print("\nAtlas validation complete.")
        return 0
    except ValidationError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
