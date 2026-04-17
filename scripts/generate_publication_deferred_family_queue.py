#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from triage_publication_tranche import build_triage_bundle

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_OUTPUT_PATH = REPO_ROOT / 'docs' / 'operations' / 'PUBLICATION-DEFERRED-FAMILY-QUEUE.md'
JSON_OUTPUT_PATH = REPO_ROOT / 'reports' / 'truth-inventory' / 'publication-deferred-family-queue.json'
TRIAGE_REPORT_PATH = REPO_ROOT / 'docs' / 'operations' / 'PUBLICATION-TRIAGE-REPORT.md'
REGISTRY_PATH = REPO_ROOT / 'config' / 'automation-backbone' / 'completion-program-registry.json'
DOCS_LIFECYCLE_REGISTRY_PATH = REPO_ROOT / 'config' / 'automation-backbone' / 'docs-lifecycle-registry.json'


def _publication_config_fingerprint(registry_path: Path) -> str:
    payload = json.loads(registry_path.read_text(encoding='utf-8'))
    publication = payload.get('publication_slices') or {}
    rendered = json.dumps(publication, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(rendered.encode('utf-8')).hexdigest()


def build_queue_bundle(
    repo_root: Path = REPO_ROOT,
    registry_path: Path = REGISTRY_PATH,
    docs_lifecycle_registry_path: Path = DOCS_LIFECYCLE_REGISTRY_PATH,
) -> dict[str, Any]:
    triage = build_triage_bundle(
        repo_root=repo_root,
        registry_path=registry_path,
        docs_lifecycle_registry_path=docs_lifecycle_registry_path,
    )
    families = []
    for record in triage['deferred_families']:
        families.append({
            'id': record['id'],
            'title': record['title'],
            'disposition': record['disposition'],
            'execution_rank': int(record.get('execution_rank') or 999),
            'execution_class': record.get('execution_class') or '',
            'next_action': record.get('next_action') or '',
            'success_condition': record.get('success_condition') or '',
            'owner_workstreams': list(record.get('owner_workstreams') or []),
            'match_count': int(record.get('match_count') or 0),
            'path_hints': list(record.get('path_hints') or []),
            'sample_paths': [entry['path'] for entry in record.get('matched_entries', [])[:12]],
            'scope': record.get('scope') or '',
        })
    families.sort(key=lambda item: (item['execution_rank'], item['id']))
    next_family = next((item for item in families if item['match_count'] > 0), None)
    return {
        'publication_config_fingerprint': _publication_config_fingerprint(registry_path),
        'active_sequence_id': triage['active_sequence_id'],
        'dirty_entries': triage['summary']['dirty_entries'],
        'slice_matched_entries': triage['summary']['slice_matched_entries'],
        'deferred_entries': triage['summary']['deferred_entries'],
        'deferred_family_count': len(families),
        'next_recommended_family': next_family,
        'families': families,
    }


def _check_via_dependency_freshness(*, repo_root: Path, registry_path: Path, markdown_output: Path, json_output: Path) -> int:
    triage_report_path = repo_root / TRIAGE_REPORT_PATH.relative_to(REPO_ROOT)
    missing_outputs: list[str] = []
    if not markdown_output.exists():
        missing_outputs.append(str(markdown_output))
    if not json_output.exists():
        missing_outputs.append(str(json_output))
    if missing_outputs:
        for path in missing_outputs:
            print(f'{path} is stale')
        return 1

    if not triage_report_path.exists():
        print(f'{triage_report_path} is stale')
        return 1

    stale = False

    try:
        json_payload = json.loads(json_output.read_text(encoding='utf-8'))
    except Exception:
        print(f'{json_output} is stale')
        return 1
    if str(json_payload.get('publication_config_fingerprint') or '') != _publication_config_fingerprint(registry_path):
        print(f'{json_output} is stale')
        stale = True
    rendered_from_json = render_markdown(json_payload)
    existing_markdown = markdown_output.read_text(encoding='utf-8')
    if existing_markdown != rendered_from_json:
        print(f'{markdown_output} is stale')
        stale = True
    return 1 if stale else 0


def render_markdown(bundle: dict[str, Any]) -> str:
    lines = [
        '# Publication Deferred-Family Queue',
        '',
        f"- Active sequence: `{bundle['active_sequence_id']}`",
        f"- Dirty entries: `{bundle['dirty_entries']}`",
        f"- Slice-matched entries: `{bundle['slice_matched_entries']}`",
        f"- Deferred-family entries: `{bundle['deferred_entries']}`",
        f"- Deferred families: `{bundle['deferred_family_count']}`",
        '',
    ]
    next_family = bundle.get('next_recommended_family')
    if next_family:
        lines.extend([
            '## Next Recommended Tranche',
            '',
            f"- Family: `{next_family['id']}`",
            f"- Title: {next_family['title']}",
            f"- Execution class: `{next_family['execution_class']}`",
            f"- Dirty matches: `{next_family['match_count']}`",
            f"- Owner workstreams: {', '.join(f'`{item}`' for item in next_family['owner_workstreams'])}",
            f"- Next action: {next_family['next_action']}",
            f"- Success condition: {next_family['success_condition']}",
            '',
        ])
    lines.extend([
        '## Ordered Queue',
        '',
        '| Rank | Family | Class | Dirty matches | Disposition | Owner workstreams |',
        '| --- | --- | --- | --- | --- | --- |',
    ])
    for family in bundle['families']:
        owners = ', '.join(family['owner_workstreams'])
        lines.append(
            f"| `{family['execution_rank']}` | `{family['id']}` | `{family['execution_class']}` | `{family['match_count']}` | `{family['disposition']}` | `{owners}` |"
        )
    for family in bundle['families']:
        lines.extend([
            '',
            f"## {family['execution_rank']}. {family['title']} (`{family['id']}`)",
            '',
            f"- Execution class: `{family['execution_class']}`",
            f"- Disposition: `{family['disposition']}`",
            f"- Dirty matches: `{family['match_count']}`",
            f"- Scope: {family['scope']}",
            f"- Next action: {family['next_action']}",
            f"- Success condition: {family['success_condition']}",
            '- Owner workstreams: ' + ', '.join(f"`{item}`" for item in family['owner_workstreams']),
        ])
        if family['sample_paths']:
            lines.extend(['', 'Sample paths:'])
            lines.extend(f"- `{path}`" for path in family['sample_paths'])
    lines.append('')
    return '\n'.join(lines)


def _json_render(bundle: dict[str, Any]) -> str:
    return json.dumps(bundle, indent=2, sort_keys=True) + '\n'


def main() -> int:
    parser = argparse.ArgumentParser(description='Render the ordered follow-on queue for publication deferred families.')
    parser.add_argument('--repo-root', type=Path, default=REPO_ROOT)
    parser.add_argument('--markdown-output', type=Path, default=DOC_OUTPUT_PATH)
    parser.add_argument('--json-output', type=Path, default=JSON_OUTPUT_PATH)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()

    if args.check:
        return _check_via_dependency_freshness(
            repo_root=args.repo_root,
            registry_path=REGISTRY_PATH if args.repo_root == REPO_ROOT else args.repo_root / REGISTRY_PATH.relative_to(REPO_ROOT),
            markdown_output=args.markdown_output,
            json_output=args.json_output,
        )

    bundle = build_queue_bundle(
        repo_root=args.repo_root,
        registry_path=REGISTRY_PATH if args.repo_root == REPO_ROOT else args.repo_root / REGISTRY_PATH.relative_to(REPO_ROOT),
        docs_lifecycle_registry_path=(
            DOCS_LIFECYCLE_REGISTRY_PATH
            if args.repo_root == REPO_ROOT
            else args.repo_root / DOCS_LIFECYCLE_REGISTRY_PATH.relative_to(REPO_ROOT)
        ),
    )
    markdown = render_markdown(bundle)
    json_payload = _json_render(bundle)

    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    existing_markdown = args.markdown_output.read_text(encoding='utf-8') if args.markdown_output.exists() else ''
    existing_json = args.json_output.read_text(encoding='utf-8') if args.json_output.exists() else ''
    if existing_markdown != markdown:
        args.markdown_output.write_text(markdown, encoding='utf-8')
    if existing_json != json_payload:
        args.json_output.write_text(json_payload, encoding='utf-8')
    print(args.markdown_output)
    print(args.json_output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
