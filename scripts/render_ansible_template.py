#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def merge_dicts(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def find_inventory_host(inventory: dict[str, Any], host_name: str) -> dict[str, Any]:
    def visit(node: Any) -> dict[str, Any] | None:
        if not isinstance(node, dict):
            return None
        hosts = node.get("hosts")
        if isinstance(hosts, dict) and host_name in hosts:
            host_vars = hosts.get(host_name) or {}
            if not isinstance(host_vars, dict):
                raise ValueError(f"Inventory host vars must be a mapping for {host_name}")
            return host_vars
        children = node.get("children")
        if isinstance(children, dict):
            for child in children.values():
                found = visit(child)
                if found is not None:
                    return found
        return None

    found = visit(inventory)
    return found or {}


def resolve_scalar(value: str, env: Environment, context: dict[str, Any]) -> str:
    template = env.from_string(value)
    rendered = template.render(**context)
    return rendered


def resolve_values(value: Any, env: Environment, context: dict[str, Any]) -> Any:
    if isinstance(value, str):
        if "{{" not in value and "{%" not in value:
            return value
        return resolve_scalar(value, env, context)
    if isinstance(value, list):
        return [resolve_values(item, env, context) for item in value]
    if isinstance(value, dict):
        return {key: resolve_values(item, env, context) for key, item in value.items()}
    return value


def build_context(ansible_root: Path, host_name: str, defaults_paths: list[Path]) -> dict[str, Any]:
    inventory = load_yaml(ansible_root / "inventory.yml")
    group_vars = load_yaml(ansible_root / "group_vars" / "all" / "main.yml")
    host_vars = load_yaml(ansible_root / "host_vars" / f"{host_name}.yml")
    inventory_host_vars = find_inventory_host(inventory, host_name)

    context: dict[str, Any] = {}
    for defaults_path in defaults_paths:
        context = merge_dicts(context, load_yaml(defaults_path))
    context = merge_dicts(context, group_vars)
    context = merge_dicts(context, inventory_host_vars)
    context = merge_dicts(context, host_vars)

    env = Environment(autoescape=False)
    env.filters["to_json"] = lambda value: json.dumps(value)

    for _ in range(4):
        resolved = resolve_values(context, env, context)
        if resolved == context:
            break
        context = resolved

    return context


def render_template(ansible_root: Path, template_path: Path, context: dict[str, Any]) -> str:
    env = Environment(
        loader=FileSystemLoader(str(ansible_root)),
        autoescape=False,
        keep_trailing_newline=True,
        trim_blocks=False,
        lstrip_blocks=False,
    )
    env.filters["to_json"] = lambda value: json.dumps(value)
    template = env.get_template(str(template_path.relative_to(ansible_root)).replace("\\", "/"))
    return template.render(**context)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render an Athanor Ansible Jinja template without ansible.")
    parser.add_argument("--ansible-root", required=True, help="Path to the ansible root directory.")
    parser.add_argument(
        "--host",
        required=True,
        help="Host vars file name without extension, e.g. vault, core, interface.",
    )
    parser.add_argument("--template", required=True, help="Path to the template file, relative to ansible root.")
    parser.add_argument(
        "--defaults",
        action="append",
        default=[],
        help="Role defaults file path relative to ansible root. May be specified multiple times.",
    )
    parser.add_argument("--output", help="Optional output file path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ansible_root = Path(args.ansible_root).resolve()
    template_path = (ansible_root / args.template).resolve()
    defaults_paths = [(ansible_root / item).resolve() for item in args.defaults]

    context = build_context(ansible_root, args.host, defaults_paths)
    rendered = render_template(ansible_root, template_path, context)

    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
