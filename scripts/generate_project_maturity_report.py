from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "config" / "automation-backbone"
PORTFOLIO_PATH = CONFIG_DIR / "project-maturity-registry.json"
TOPOLOGY_PATH = CONFIG_DIR / "platform-topology.json"
WORKFLOW_PATH = REPO_ROOT / ".gitea" / "workflows" / "ci.yml"
OUTPUT_PATH = REPO_ROOT / "docs" / "operations" / "PROJECT-MATURITY-REPORT.md"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def workflow_step_names() -> set[str]:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    return {
        match.group(1).strip()
        for match in re.finditer(r"^\s*-\s+name:\s*(.+?)\s*$", content, re.MULTILINE)
    }


def requirement_map(registry: dict) -> dict[str, list[str]]:
    return {
        str(entry.get("id") or ""): [str(item) for item in entry.get("requirements", [])]
        for entry in registry.get("classes", [])
    }


def missing_requirements(
    project: dict,
    requirements: list[str],
    service_ids: set[str],
    step_names: set[str],
) -> list[str]:
    issues: list[str] = []
    project_id = str(project.get("id") or "")

    for requirement in requirements:
        if requirement == "owner" and not str(project.get("owner") or "").strip():
            issues.append("missing owner")
        elif requirement == "workspace":
            workspace = REPO_ROOT / str(project.get("workspace") or "")
            if not workspace.exists():
                issues.append(f"missing workspace `{project.get('workspace')}`")
        elif requirement == "docs":
            docs = [str(item) for item in project.get("docs", []) if str(item).strip()]
            if not docs:
                issues.append("missing docs")
            else:
                for doc in docs:
                    if not (REPO_ROOT / doc).exists():
                        issues.append(f"missing doc `{doc}`")
        elif requirement == "env_example":
            env_example = str(project.get("env_example") or "").strip()
            if not env_example:
                issues.append("missing env example")
            elif not (REPO_ROOT / env_example).exists():
                issues.append(f"missing env example `{env_example}`")
        elif requirement == "ci":
            ci_commands = [str(item).strip() for item in project.get("ci", []) if str(item).strip()]
            ci_steps = [str(item).strip() for item in project.get("ci_workflow_steps", []) if str(item).strip()]
            if not ci_commands:
                issues.append("missing ci commands")
            if not ci_steps:
                issues.append("missing CI workflow step mapping")
            else:
                missing_steps = [step for step in ci_steps if step not in step_names]
                if missing_steps:
                    issues.append(f"workflow missing CI steps for `{project_id}`: {', '.join(missing_steps)}")
        elif requirement == "monitoring":
            monitoring = [str(item).strip() for item in project.get("monitoring", []) if str(item).strip()]
            if not monitoring:
                issues.append("missing monitoring services")
            else:
                unknown = [item for item in monitoring if item not in service_ids]
                if unknown:
                    issues.append(f"unknown monitoring services: {', '.join(unknown)}")
        elif requirement == "acceptance_gate":
            gates = [str(item).strip() for item in project.get("acceptance_gate", []) if str(item).strip()]
            gate_steps = [
                str(item).strip()
                for item in project.get("acceptance_workflow_steps", [])
                if str(item).strip()
            ]
            if not gates:
                issues.append("missing acceptance gate commands")
            if not gate_steps:
                issues.append("missing acceptance workflow step mapping")
            else:
                missing_steps = [step for step in gate_steps if step not in step_names]
                if missing_steps:
                    issues.append(
                        f"workflow missing acceptance steps for `{project_id}`: {', '.join(missing_steps)}"
                    )
        elif requirement == "explicit_status" and not str(project.get("explicit_status") or "").strip():
            issues.append("missing explicit status")
        elif requirement == "archive_note" and not str(project.get("archive_note") or "").strip():
            issues.append("missing archive note")

    return issues


def render_project_maturity_report(portfolio: dict, topology: dict) -> str:
    service_ids = {str(service.get("id") or "") for service in topology.get("services", [])}
    step_names = workflow_step_names()
    requirements_by_class = requirement_map(portfolio)
    projects = list(portfolio.get("projects", []))
    class_counts = Counter(str(project.get("class") or "unknown") for project in projects)

    evaluated_projects = []
    ready_count = 0
    for project in projects:
        project_class = str(project.get("class") or "")
        issues = missing_requirements(
            project,
            requirements_by_class.get(project_class, []),
            service_ids,
            step_names,
        )
        if not issues:
            ready_count += 1
        evaluated_projects.append((project, issues))

    lines = [
        "# Project Maturity Report",
        "",
        "Generated from `config/automation-backbone/project-maturity-registry.json` by `scripts/generate_project_maturity_report.py`.",
        "Do not edit manually.",
        "",
        "## Summary",
        "",
        f"- Registry version: `{portfolio.get('version', 'unknown')}`",
        f"- Projects tracked: `{len(projects)}`",
        f"- Projects meeting declared class: `{ready_count}`",
        "",
        "| Class | Count |",
        "| --- | ---: |",
    ]
    for class_id in [str(entry.get("id") or "") for entry in portfolio.get("classes", [])]:
        lines.append(f"| `{class_id}` | {class_counts.get(class_id, 0)} |")

    lines.extend(
        [
            "",
            "## Project Status",
            "",
            "| Project | Class | Status | Owner | Workspace |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for project, issues in evaluated_projects:
        project_id = str(project.get("id") or "")
        label = str(project.get("label") or project_id)
        project_class = str(project.get("class") or "")
        status = "meets declared class" if not issues else "needs attention"
        lines.append(
            f"| `{project_id}` ({label}) | `{project_class}` | {status} | "
            f"`{project.get('owner', '')}` | `{project.get('workspace', '')}` |"
        )

    for project, issues in evaluated_projects:
        project_id = str(project.get("id") or "")
        label = str(project.get("label") or project_id)
        project_class = str(project.get("class") or "")
        requirements = requirements_by_class.get(project_class, [])
        ci_steps = [str(item) for item in project.get("ci_workflow_steps", []) if str(item).strip()]
        acceptance_steps = [
            str(item) for item in project.get("acceptance_workflow_steps", [])
            if str(item).strip()
        ]

        lines.extend(
            [
                "",
                f"## {label} (`{project_id}`)",
                "",
                f"- Class: `{project_class}`",
                f"- Owner: `{project.get('owner', '')}`",
                f"- Workspace: `{project.get('workspace', '')}`",
                f"- Declared requirements: {', '.join(f'`{item}`' for item in requirements) or 'none'}",
                f"- Monitoring: {', '.join(f'`{item}`' for item in project.get('monitoring', [])) or 'none'}",
                f"- CI workflow steps: {', '.join(f'`{item}`' for item in ci_steps) or 'none'}",
                f"- Acceptance workflow steps: {', '.join(f'`{item}`' for item in acceptance_steps) or 'none'}",
            ]
        )

        docs = [str(item) for item in project.get("docs", []) if str(item).strip()]
        if docs:
            lines.append(f"- Docs: {', '.join(f'`{item}`' for item in docs)}")

        ci_commands = [str(item) for item in project.get("ci", []) if str(item).strip()]
        if ci_commands:
            lines.append("- CI commands:")
            for command in ci_commands:
                lines.append(f"  - `{command}`")

        acceptance_gates = [str(item) for item in project.get("acceptance_gate", []) if str(item).strip()]
        if acceptance_gates:
            lines.append("- Acceptance gate:")
            for command in acceptance_gates:
                lines.append(f"  - `{command}`")

        note = str(project.get("notes") or "").strip()
        if note:
            lines.append(f"- Notes: {note}")

        if issues:
            lines.append("- Open issues:")
            for issue in issues:
                lines.append(f"  - {issue}")
        else:
            lines.append("- Open issues: none")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if the generated output is stale.")
    args = parser.parse_args()

    rendered = render_project_maturity_report(load_json(PORTFOLIO_PATH), load_json(TOPOLOGY_PATH))
    if args.check:
        existing = OUTPUT_PATH.read_text(encoding="utf-8")
        if existing != rendered:
            print(f"{OUTPUT_PATH.relative_to(REPO_ROOT).as_posix()} is stale")
            return 1
        return 0

    OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
