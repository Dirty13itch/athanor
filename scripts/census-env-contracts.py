#!/usr/bin/env python3
"""Inventory environment and config contracts across Athanor repo layers."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

from completion_audit_common import (
    AGENTS_ROOT,
    ATLAS_COMPLETION_DIR,
    DASHBOARD_ROOT,
    ENV_PATTERNS,
    REPO_ROOT,
    extract_env_names,
    read_text,
    write_json,
)


OUTPUT_PATH = ATLAS_COMPLETION_DIR / "env-contract-census.json"
SCAN_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".sh", ".ps1", ".yml", ".yaml", ".j2", ".env", ".example", ".toml"}
AGENT_CONFIG_PATH = AGENTS_ROOT / "src" / "athanor_agents" / "config.py"


def classify_env(name: str) -> str:
    if name.startswith("NEXT_PUBLIC_"):
        return "public-runtime"
    if name.startswith("ATHANOR_"):
        return "cluster-runtime"
    if name.endswith("_API_KEY") or name.endswith("_PASSWORD") or name.endswith("_TOKEN"):
        return "secret"
    return "supporting"


def is_export_source(path: Path) -> bool:
    text = path.as_posix()
    return any(
        marker in text
        for marker in (
            "docker-compose",
            ".env.example",
            "/ansible/",
            "/templates/",
            "/defaults/",
        )
    )


def should_mark_broken(env_name: str, consumer_sources: list[str], export_sources: list[str]) -> bool:
    if export_sources:
        return False
    if not env_name.startswith(("ATHANOR_", "NEXT_PUBLIC_", "VAPID_")):
        return False
    critical_prefixes = (
        "projects/dashboard/",
        "projects/agents/",
        "ansible/roles/",
        "projects/dashboard/src/lib/",
        "projects/agents/src/athanor_agents/",
    )
    if not any(source.startswith(critical_prefixes) for source in consumer_sources):
        return False
    legacy_aliases = {
        "ATHANOR_LLM_API_KEY",
        "ATHANOR_LLM_BASE_URL",
        "ATHANOR_EOBQ_URL",
        "ATHANOR_NODE1_VLLM_URL",
        "ATHANOR_NODE2_VLLM_URL",
    }
    return env_name not in legacy_aliases


def parse_defaulted_agent_envs() -> set[str]:
    if not AGENT_CONFIG_PATH.exists():
        return set()

    tree = ast.parse(read_text(AGENT_CONFIG_PATH))
    defaulted_envs: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.AnnAssign):
            continue
        value = node.value
        if not isinstance(value, ast.Call) or getattr(value.func, "id", None) != "Field":
            continue

        has_default = False
        if value.args:
            has_default = True
        for keyword in value.keywords:
            if keyword.arg == "default":
                has_default = True
                break
        if not has_default:
            continue

        for keyword in value.keywords:
            if keyword.arg != "validation_alias":
                continue
            alias_call = keyword.value
            if not isinstance(alias_call, ast.Call) or getattr(alias_call.func, "id", None) != "AliasChoices":
                continue
            for arg in alias_call.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    defaulted_envs.add(arg.value)

    return defaulted_envs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(OUTPUT_PATH))
    args = parser.parse_args()

    defaulted_envs = parse_defaulted_agent_envs()
    records: dict[str, dict] = {}
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SCAN_SUFFIXES and path.name not in {".env.example"}:
            continue
        if any(
            part in {".next", "node_modules", "__pycache__", ".git"}
            or part.startswith(".next-playwright")
            for part in path.parts
        ):
            continue

        env_names = extract_env_names(read_text(path))
        if not env_names:
            continue

        relative = path.relative_to(REPO_ROOT).as_posix()
        for env_name in sorted(env_names):
            record = records.setdefault(
                env_name,
                {
                    "name": env_name,
                    "classification": classify_env(env_name),
                    "consumerSources": [],
                    "exportSources": [],
                    "notes": [],
                },
            )
            if is_export_source(path):
                record["exportSources"].append(relative)
            else:
                record["consumerSources"].append(relative)

    items = []
    for env_name, record in sorted(records.items()):
        completion_status = "live_partial"
        if env_name in defaulted_envs:
            record["notes"].append("Default-backed settings alias; repo code provides a fallback value.")
        elif should_mark_broken(env_name, record["consumerSources"], record["exportSources"]):
            completion_status = "broken"
            record["notes"].append("No repo-side export source found for a runtime-critical env.")
        elif record["classification"] == "secret":
            record["notes"].append("Secret-valued env; inventory only, do not commit live values.")
        items.append(
            {
                "name": env_name,
                "classification": record["classification"],
                "consumerSources": sorted(set(record["consumerSources"])),
                "exportSources": sorted(set(record["exportSources"])),
                "completionStatus": completion_status,
                "notes": record["notes"],
            }
        )

    output_path = Path(args.output)
    write_json(output_path, items)
    print(
        json.dumps(
            {
                "output": str(output_path),
                "envCount": len(items),
                "brokenCount": sum(1 for item in items if item["completionStatus"] == "broken"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
