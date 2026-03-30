from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "config" / "automation-backbone" / "docs-lifecycle-registry.json"
OUTPUT_PATH = REPO_ROOT / "docs" / "DOCUMENTATION-INDEX.md"
CLASS_ORDER = ("canonical", "generated", "reference", "archive")


def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def classify_kind(path: Path) -> str:
    if path.is_dir():
        return "directory"
    if path.suffix.lower() == ".md":
        return "markdown"
    return "path"


def render_documentation_index(registry: dict) -> str:
    documents = list(registry.get("documents", []))
    counts = Counter(str(document.get("class") or "unknown") for document in documents)

    lines = [
        "# Documentation Index",
        "",
        "Generated from `config/automation-backbone/docs-lifecycle-registry.json` by `scripts/generate_documentation_index.py`.",
        "Do not edit manually.",
        "",
        "## Summary",
        "",
        f"- Registry version: `{registry.get('version', 'unknown')}`",
        f"- Total tracked entries: `{len(documents)}`",
        "",
        "| Class | Count |",
        "| --- | ---: |",
    ]
    for doc_class in CLASS_ORDER:
        lines.append(f"| `{doc_class}` | {counts.get(doc_class, 0)} |")

    for doc_class in CLASS_ORDER:
        class_documents = [
            document
            for document in documents
            if str(document.get("class") or "") == doc_class
        ]
        if not class_documents:
            continue

        lines.extend(
            [
                "",
                f"## {doc_class.replace('_', ' ').title()}",
                "",
                "| Path | Kind | Owner |",
                "| --- | --- | --- |",
            ]
        )

        for document in sorted(class_documents, key=lambda item: str(item.get("path") or "")):
            relative_path = str(document.get("path") or "")
            path = REPO_ROOT / relative_path
            owner = str(document.get("owner") or "")
            lines.append(f"| `{relative_path}` | {classify_kind(path)} | `{owner}` |")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if the generated output is stale.")
    args = parser.parse_args()

    rendered = render_documentation_index(load_registry())
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
