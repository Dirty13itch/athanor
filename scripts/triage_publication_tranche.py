#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY_PATH = REPO_ROOT / "config" / "automation-backbone" / "completion-program-registry.json"
DEFAULT_DOCS_LIFECYCLE_REGISTRY_PATH = REPO_ROOT / "config" / "automation-backbone" / "docs-lifecycle-registry.json"
LOCAL_NOISE_HINTS = [
    ".letta/",
    "evals/.letta/",
    "output/",
    "__pycache__/",
    ".pytest_cache/",
    "node_modules/",
]

SELF_MANAGED_GENERATOR_SCRIPTS = (
    'scripts/triage_publication_tranche.py',
    'scripts/generate_publication_deferred_family_queue.py',
    'scripts/write_steady_state_status.py',
    'scripts/generate_full_system_audit.py',
    'scripts/generate_ecosystem_master_plan.py',
)

SELF_MANAGED_GENERATOR_SIDECARS = {
    'scripts/generate_publication_deferred_family_queue.py': [
        'reports/truth-inventory/publication-deferred-family-queue.json',
    ],
    'scripts/write_steady_state_status.py': [
        'reports/truth-inventory/steady-state-status.json',
        'reports/truth-inventory/steady-state-live.md',
    ],
    'scripts/generate_full_system_audit.py': [
        'reports/truth-inventory/full-system-audit-index.json',
        'reports/truth-inventory/full-system-audit-findings.json',
        'reports/truth-inventory/full-system-audit-scorecard.json',
    ],
    'scripts/generate_ecosystem_master_plan.py': [
        'reports/truth-inventory/ecosystem-master-plan.json',
    ],
}


GIT_STATUS_TIMEOUT_SECONDS = 20


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _self_managed_output_paths(docs_lifecycle_registry_path: Path) -> set[str]:
    if not docs_lifecycle_registry_path.exists():
        return set()

    payload = _load_json(docs_lifecycle_registry_path)
    outputs: set[str] = set()
    for entry in payload.get('documents', []):
        if not isinstance(entry, dict):
            continue
        generator = _normalize_path(str(entry.get('generator') or ''))
        path = _normalize_path(str(entry.get('path') or ''))
        if not generator or not path:
            continue
        matched_script = next((script for script in SELF_MANAGED_GENERATOR_SCRIPTS if script in generator), None)
        if matched_script is None:
            continue
        outputs.add(path)
        outputs.update(_normalize_path(item) for item in SELF_MANAGED_GENERATOR_SIDECARS.get(matched_script, []))
    return outputs


def _normalize_path(value: str) -> str:
    normalized = str(value).strip().replace('\\', '/')
    while normalized.startswith('./'):
        normalized = normalized[2:]
    return normalized


def _match_score(path: str, hint: str) -> tuple[int, int] | None:
    normalized_path = _normalize_path(path)
    normalized_hint = _normalize_path(hint)
    if not normalized_hint:
        return None
    if normalized_path == normalized_hint:
        return (3, len(normalized_hint))
    if normalized_hint.endswith(('/', '-', '_')):
        if normalized_path.startswith(normalized_hint):
            return (2, len(normalized_hint))
        return None
    if normalized_path.startswith(normalized_hint + '/'):
        return (1, len(normalized_hint))
    return None


def _matches_hint(path: str, hint: str) -> bool:
    return _match_score(path, hint) is not None


def _resolve_path(repo_root: Path, value: str) -> Path:
    normalized = _normalize_path(value)
    if normalized.startswith('/mnt/'):
        return Path(normalized)
    if normalized.startswith('C:/'):
        return Path('/mnt/c') / normalized.removeprefix('C:/')
    return repo_root / normalized


WINDOWS_GIT_EXE = Path('/mnt/c/Program Files/Git/cmd/git.exe')


def _to_windows_path(path: Path) -> str | None:
    normalized = path.as_posix()
    if not normalized.startswith('/mnt/c/'):
        return None
    suffix = normalized.removeprefix('/mnt/c/').replace('/', '\\')
    return f'C:\\{suffix}'


def _git_command(repo_root: Path, *args: str) -> list[str]:
    windows_repo = _to_windows_path(repo_root)
    if windows_repo and WINDOWS_GIT_EXE.exists():
        return [str(WINDOWS_GIT_EXE), '-C', windows_repo, *args]
    return ['git', '-C', str(repo_root), *args]


def _git_command_candidates(repo_root: Path, *args: str) -> list[list[str]]:
    candidates: list[list[str]] = []
    windows_repo = _to_windows_path(repo_root)
    if windows_repo and WINDOWS_GIT_EXE.exists():
        candidates.append([str(WINDOWS_GIT_EXE), '-C', windows_repo, *args])
    candidates.append(['git', '-C', str(repo_root), *args])

    deduped: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for candidate in candidates:
        key = tuple(candidate)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _git_status_entries(repo_root: Path) -> list[dict[str, str]]:
    completed = None
    failures: list[str] = []
    for command in _git_command_candidates(repo_root, 'status', '--short', '--untracked-files=normal', '--no-renames'):
        try:
            attempt = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=GIT_STATUS_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            failures.append(f"{' '.join(command)} -> {exc}")
            continue
        if attempt.returncode == 0:
            completed = attempt
            break
        failures.append(
            f"{' '.join(command)} -> code {attempt.returncode}: {(attempt.stderr or attempt.stdout).strip()}"
        )

    if completed is None:
        raise RuntimeError('git status failed: ' + ' | '.join(failures))

    entries: list[dict[str, str]] = []
    for raw_line in completed.stdout.splitlines():
        if not raw_line:
            continue
        status = raw_line[:2]
        path = raw_line[3:] if len(raw_line) > 3 else ''
        entries.append({'status': status, 'path': _normalize_path(path)})
    return entries


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        normalized = _normalize_path(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def _slice_records(registry_payload: dict[str, Any]) -> list[dict[str, Any]]:
    publication = dict(registry_payload.get('publication_slices') or {})
    records: list[dict[str, Any]] = []
    for entry in publication.get('slices', []):
        if not isinstance(entry, dict):
            continue
        publication_artifacts = [str(item).strip() for item in entry.get('publication_artifact_refs', []) if str(item).strip()]
        generated_artifacts = [str(item).strip() for item in entry.get('generated_artifacts', []) if str(item).strip()]
        working_tree_hints = [str(item).strip() for item in entry.get('working_tree_path_hints', []) if str(item).strip()]
        records.append({
            'id': str(entry.get('id') or '').strip(),
            'title': str(entry.get('title') or '').strip(),
            'status': str(entry.get('status') or '').strip(),
            'publication_artifact_refs': publication_artifacts,
            'generated_artifacts': generated_artifacts,
            'working_tree_path_hints': working_tree_hints,
            'all_hints': _dedupe(working_tree_hints + publication_artifacts + generated_artifacts),
        })
    return records


def _deferred_family_records(registry_payload: dict[str, Any]) -> list[dict[str, Any]]:
    publication = dict(registry_payload.get('publication_slices') or {})
    records: list[dict[str, Any]] = []
    for entry in publication.get('deferred_families', []):
        if not isinstance(entry, dict):
            continue
        records.append({
            'id': str(entry.get('id') or '').strip(),
            'title': str(entry.get('title') or '').strip(),
            'disposition': str(entry.get('disposition') or '').strip(),
            'scope': str(entry.get('scope') or '').strip(),
            'execution_rank': int(entry.get('execution_rank') or 999),
            'execution_class': str(entry.get('execution_class') or '').strip(),
            'next_action': str(entry.get('next_action') or '').strip(),
            'success_condition': str(entry.get('success_condition') or '').strip(),
            'owner_workstreams': [str(item).strip() for item in entry.get('owner_workstreams', []) if str(item).strip()],
            'path_hints': _dedupe([str(item).strip() for item in entry.get('path_hints', []) if str(item).strip()]),
        })
    return records


def _best_matches(path: str, records: list[dict[str, Any]], *, hint_field: str) -> list[dict[str, Any]]:
    scored: list[tuple[dict[str, Any], tuple[int, int]]] = []
    for record in records:
        best_score: tuple[int, int] | None = None
        for hint in record.get(hint_field, []):
            score = _match_score(path, hint)
            if score is None:
                continue
            if best_score is None or score > best_score:
                best_score = score
        if best_score is not None:
            scored.append((record, best_score))
    if not scored:
        return []
    strongest = max(score for _, score in scored)
    return [record for record, score in scored if score == strongest]


def build_triage_bundle(
    *,
    repo_root: Path = REPO_ROOT,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
    docs_lifecycle_registry_path: Path = DEFAULT_DOCS_LIFECYCLE_REGISTRY_PATH,
) -> dict[str, Any]:
    registry_payload = _load_json(registry_path)
    slice_records = _slice_records(registry_payload)
    deferred_records = _deferred_family_records(registry_payload)
    self_managed_outputs = _self_managed_output_paths(docs_lifecycle_registry_path)
    entries = [
        entry
        for entry in _git_status_entries(repo_root)
        if entry['path'] not in self_managed_outputs
    ]

    matched: dict[str, list[dict[str, str]]] = {record['id']: [] for record in slice_records}
    deferred: dict[str, list[dict[str, str]]] = {record['id']: [] for record in deferred_records}
    ambiguous: list[dict[str, Any]] = []
    unclassified: list[dict[str, str]] = []
    local_noise: list[dict[str, str]] = []

    for entry in entries:
        path = entry['path']
        if any(_matches_hint(path, hint) for hint in LOCAL_NOISE_HINTS):
            local_noise.append(entry)
            continue
        matching_slices = _best_matches(path, slice_records, hint_field='all_hints')
        if len(matching_slices) == 1:
            matched[matching_slices[0]['id']].append(entry)
            continue
        if len(matching_slices) > 1:
            ambiguous.append({
                'status': entry['status'],
                'path': path,
                'match_class': 'publication_slice',
                'matching_targets': [record['id'] for record in matching_slices],
            })
            continue
        matching_deferred = _best_matches(path, deferred_records, hint_field='path_hints')
        if len(matching_deferred) == 1:
            deferred[matching_deferred[0]['id']].append(entry)
        elif len(matching_deferred) > 1:
            ambiguous.append({
                'status': entry['status'],
                'path': path,
                'match_class': 'deferred_family',
                'matching_targets': [record['id'] for record in matching_deferred],
            })
        else:
            unclassified.append(entry)

    slices: list[dict[str, Any]] = []
    for record in slice_records:
        missing_artifacts = [
            ref for ref in record['publication_artifact_refs']
            if not _resolve_path(repo_root, ref).exists()
        ]
        missing_generated = [
            ref for ref in record['generated_artifacts']
            if not _resolve_path(repo_root, ref).exists()
        ]
        slices.append({
            **record,
            'match_count': len(matched[record['id']]),
            'matched_entries': matched[record['id']],
            'missing_publication_artifacts': missing_artifacts,
            'missing_generated_artifacts': missing_generated,
        })

    deferred_families: list[dict[str, Any]] = []
    for record in sorted(deferred_records, key=lambda item: (item.get('execution_rank', 999), item['id'])):
        deferred_families.append({
            **record,
            'match_count': len(deferred[record['id']]),
            'matched_entries': deferred[record['id']],
        })

    publication = dict(registry_payload.get('publication_slices') or {})
    return {
        'generated_at': _iso_now(),
        'repo_root': str(repo_root),
        'registry_path': str(registry_path),
        'docs_lifecycle_registry_path': str(docs_lifecycle_registry_path),
        'active_sequence_id': str(publication.get('active_sequence_id') or ''),
        'summary': {
            'dirty_entries': len(entries),
            'slice_matched_entries': sum(len(items) for items in matched.values()),
            'deferred_entries': sum(len(items) for items in deferred.values()),
            'ambiguous_entries': len(ambiguous),
            'unclassified_entries': len(unclassified),
            'local_noise_entries': len(local_noise),
        },
        'slices': slices,
        'deferred_families': deferred_families,
        'ambiguous_entries': ambiguous,
        'unclassified_entries': unclassified,
        'local_noise_entries': local_noise,
    }


def _sample(entries: list[dict[str, Any]], limit: int) -> list[str]:
    return [f"`{entry['status'].strip() or '??'}` {entry['path']}" for entry in entries[:limit]]


def _normalize_rendered_for_check(rendered: str, *, output_format: str) -> str:
    if output_format == 'json':
        payload = json.loads(rendered)
        payload.pop('generated_at', None)
        return json.dumps(payload, indent=2, sort_keys=True) + '\n'
    lines = []
    for line in rendered.splitlines():
        if line.startswith('Generated: `'):
            continue
        lines.append(line)
    return '\n'.join(lines) + '\n'


def render_markdown(bundle: dict[str, Any], *, limit: int = 12) -> str:
    lines = [
        '# Publication Triage Summary',
        '',
        f"- Active sequence: `{bundle['active_sequence_id']}`",
        f"- Dirty entries: `{bundle['summary']['dirty_entries']}`",
        f"- Slice-matched entries: `{bundle['summary']['slice_matched_entries']}`",
        f"- Deferred-family entries: `{bundle['summary']['deferred_entries']}`",
        f"- Ambiguous entries: `{bundle['summary']['ambiguous_entries']}`",
        f"- Unclassified entries: `{bundle['summary']['unclassified_entries']}`",
        f"- Local-noise entries: `{bundle['summary']['local_noise_entries']}`",
        '',
        '## Slice Coverage',
        '',
        '| Slice | Status | Dirty matches | Missing publication refs | Missing generated artifacts |',
        '| --- | --- | --- | --- | --- |',
    ]
    for record in bundle['slices']:
        lines.append(
            f"| `{record['id']}` | `{record['status']}` | `{record['match_count']}` | `{len(record['missing_publication_artifacts'])}` | `{len(record['missing_generated_artifacts'])}` |"
        )
    for record in bundle['slices']:
        lines.extend([
            '',
            f"## {record['title']} (`{record['id']}`)",
            '',
            f"- Dirty matches: `{record['match_count']}`",
            f"- Publication refs: `{len(record['publication_artifact_refs'])}`",
            f"- Working-tree hints: `{len(record['working_tree_path_hints'])}`",
            f"- Missing publication refs: `{len(record['missing_publication_artifacts'])}`",
            f"- Missing generated artifacts: `{len(record['missing_generated_artifacts'])}`",
        ])
        sample = _sample(record['matched_entries'], limit)
        if sample:
            lines.extend(['', 'Sample dirty paths:'])
            lines.extend(f"- {item}" for item in sample)
        if record['missing_publication_artifacts']:
            lines.extend(['', 'Missing publication refs:'])
            lines.extend(f"- `{item}`" for item in record['missing_publication_artifacts'][:limit])
        if record['missing_generated_artifacts']:
            lines.extend(['', 'Missing generated artifacts:'])
            lines.extend(f"- `{item}`" for item in record['missing_generated_artifacts'][:limit])
    if bundle['deferred_families']:
        lines.extend([
            '',
            '## Deferred Family Coverage',
            '',
            '| Deferred family | Disposition | Dirty matches |',
            '| --- | --- | --- |',
        ])
        for record in bundle['deferred_families']:
            lines.append(f"| `{record['id']}` | `{record['disposition']}` | `{record['match_count']}` |")
        for record in bundle['deferred_families']:
            lines.extend([
                '',
                f"## Deferred: {record['title']} (`{record['id']}`)",
                '',
                f"- Disposition: `{record['disposition']}`",
                f"- Dirty matches: `{record['match_count']}`",
                f"- Path hints: `{len(record['path_hints'])}`",
            ])
            if record['scope']:
                lines.append(f"- Scope: {record['scope']}")
            if record.get('execution_class'):
                lines.append(f"- Execution class: `{record['execution_class']}`")
            if record.get('next_action'):
                lines.append(f"- Next action: {record['next_action']}")
            if record.get('success_condition'):
                lines.append(f"- Success condition: {record['success_condition']}")
            if record['owner_workstreams']:
                lines.append('- Owner workstreams: ' + ', '.join(f"`{item}`" for item in record['owner_workstreams']))
            sample = _sample(record['matched_entries'], limit)
            if sample:
                lines.extend(['', 'Sample dirty paths:'])
                lines.extend(f"- {item}" for item in sample)
    if bundle['ambiguous_entries']:
        lines.extend(['', '## Ambiguous Entries', ''])
        for entry in bundle['ambiguous_entries'][:limit]:
            labels = ', '.join('`' + item + '`' for item in entry['matching_targets'])
            lines.append(
                f"- `{entry['status'].strip() or '??'}` {entry['path']} -> {labels} (`{entry['match_class']}`)"
            )
    if bundle['unclassified_entries']:
        lines.extend(['', '## Unclassified Entries', ''])
        lines.extend(f"- {item}" for item in _sample(bundle['unclassified_entries'], limit))
    if bundle['local_noise_entries']:
        lines.extend(['', '## Local Noise', ''])
        lines.extend(f"- {item}" for item in _sample(bundle['local_noise_entries'], limit))
    lines.append('')
    return '\n'.join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description='Classify the current Athanor dirty tranche against publication-slice manifests.')
    parser.add_argument('--repo-root', type=Path, default=REPO_ROOT)
    parser.add_argument('--registry', type=Path, default=DEFAULT_REGISTRY_PATH)
    parser.add_argument('--docs-lifecycle-registry', type=Path, default=DEFAULT_DOCS_LIFECYCLE_REGISTRY_PATH)
    parser.add_argument('--format', choices=('markdown', 'json'), default='markdown')
    parser.add_argument('--limit', type=int, default=12)
    parser.add_argument('--write', type=Path, default=None)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()

    bundle = build_triage_bundle(
        repo_root=args.repo_root,
        registry_path=args.registry,
        docs_lifecycle_registry_path=args.docs_lifecycle_registry,
    )
    rendered = (
        json.dumps(bundle, indent=2, sort_keys=True) + '\n'
        if args.format == 'json'
        else render_markdown(bundle, limit=args.limit)
    )
    if args.check:
        if args.write is None:
            parser.error('--check requires --write so the rendered output has a freshness target')
        existing = args.write.read_text(encoding='utf-8') if args.write.exists() else ''
        if _normalize_rendered_for_check(existing, output_format=args.format) != _normalize_rendered_for_check(rendered, output_format=args.format):
            print(f'{args.write} is stale')
            return 1
        return 0
    if args.write is not None:
        existing = args.write.read_text(encoding='utf-8') if args.write.exists() else ''
        if _normalize_rendered_for_check(existing, output_format=args.format) != _normalize_rendered_for_check(rendered, output_format=args.format):
            args.write.write_text(rendered, encoding='utf-8')
        print(args.write)
    else:
        print(rendered, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
