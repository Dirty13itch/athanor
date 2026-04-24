#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from cluster_config import get_url

DEFAULT_WORKFLOW_PATH = PROJECT_ROOT / "comfyui" / "flux-scene.json"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "NEW"
CANDIDATE_OUTPUT_DIR = REPO_ROOT / "reports" / "truth-inventory" / "project-output-candidates"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "scene-pack"


def _relative_to_repo(path: Path) -> str:
    resolved = path.resolve()
    repo_root = REPO_ROOT.resolve()
    if resolved.is_relative_to(repo_root):
        return resolved.relative_to(repo_root).as_posix()
    return resolved.as_posix()


def load_workflow(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def inject_scene_prompt(
    workflow: dict[str, Any],
    *,
    prompt: str,
    seed: int,
    filename_prefix: str,
) -> dict[str, Any]:
    result = copy.deepcopy(workflow)
    result["3"]["inputs"]["text"] = prompt
    result["7"]["inputs"]["seed"] = seed
    result["10"]["inputs"]["filename_prefix"] = filename_prefix
    return result


def _http_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    *,
    timeout_seconds: int,
) -> dict[str, Any]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, method=method, headers=headers)
    with urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def queue_workflow(comfyui_url: str, workflow: dict[str, Any], *, timeout_seconds: int) -> str:
    payload = _http_json(
        "POST",
        f"{comfyui_url.rstrip('/')}/prompt",
        {"prompt": workflow},
        timeout_seconds=timeout_seconds,
    )
    prompt_id = str(payload.get("prompt_id") or "").strip()
    if not prompt_id:
        raise RuntimeError("ComfyUI did not return a prompt_id")
    return prompt_id


def poll_for_output(
    comfyui_url: str,
    prompt_id: str,
    *,
    timeout_seconds: int,
    poll_interval_seconds: float = 1.0,
) -> dict[str, str]:
    started = time.time()
    history_url = f"{comfyui_url.rstrip('/')}/history/{prompt_id}"
    while time.time() - started < timeout_seconds:
        time.sleep(poll_interval_seconds)
        payload = _http_json("GET", history_url, timeout_seconds=timeout_seconds)
        prompt_payload = dict(payload.get(prompt_id) or {})
        status = dict(prompt_payload.get("status") or {})
        if status.get("status_str") == "error":
            raise RuntimeError(f"ComfyUI marked prompt {prompt_id} as error")
        outputs = dict(prompt_payload.get("outputs") or {})
        for node_output in outputs.values():
            if not isinstance(node_output, dict):
                continue
            for key in ("images", "gifs", "videos"):
                files = node_output.get(key)
                if not isinstance(files, list) or not files:
                    continue
                first = files[0]
                if not isinstance(first, dict):
                    continue
                filename = str(first.get("filename") or "").strip()
                subfolder = str(first.get("subfolder") or "").strip()
                file_type = str(first.get("type") or "").strip()
                if filename and file_type:
                    return {
                        "filename": filename,
                        "subfolder": subfolder,
                        "type": file_type,
                    }
    raise TimeoutError(f"Timed out waiting for ComfyUI output for prompt {prompt_id}")


def build_view_url(comfyui_url: str, file_ref: dict[str, str]) -> str:
    query = urlencode(
        {
            "filename": file_ref["filename"],
            "subfolder": file_ref["subfolder"],
            "type": file_ref["type"],
        }
    )
    return f"{comfyui_url.rstrip('/')}/view?{query}"


def download_asset(asset_url: str, destination: Path, *, timeout_seconds: int) -> None:
    request = Request(asset_url, method="GET")
    with urlopen(request, timeout=timeout_seconds) as response:
        payload = response.read()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)


def write_bundle_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_project_output_candidate(manifest: dict[str, Any]) -> dict[str, Any]:
    bundle_id = str(manifest.get("bundle_id") or "").strip() or "scene-pack"
    project_id = str(manifest.get("project_id") or "eoq").strip() or "eoq"
    deliverable_refs = [
        ref
        for ref in [
            str(manifest.get("asset_ref") or "").strip(),
            str(manifest.get("manifest_ref") or "").strip(),
            str(manifest.get("collection_manifest_ref") or "").strip(),
        ]
        if ref
    ]
    workflow_ref = str(manifest.get("workflow_ref") or "").strip()
    return {
        "generated_at": str(manifest.get("generated_at") or _iso_now()),
        "candidate_id": f"{project_id}-{bundle_id}",
        "project_id": project_id,
        "title": f"EOQ scene pack: {str(manifest.get('scene_name') or bundle_id).strip()}",
        "deliverable_kind": str(manifest.get("deliverable_kind") or "content_artifact").strip() or "content_artifact",
        "deliverable_refs": deliverable_refs,
        "manifest_ref": str(manifest.get("manifest_ref") or "").strip(),
        "workflow_refs": [workflow_ref] if workflow_ref else [],
        "verification_refs": [item for item in [*deliverable_refs, workflow_ref] if item],
        "verification_status": "passed",
        "approval_posture": "hybrid",
        "acceptance_state": "pending_materialization",
        "acceptance_mode": "hybrid",
        "accepted_by": None,
        "accepted_at": None,
        "acceptance_proof_refs": [],
        "operator_steered": False,
        "beneficiary_surface": "eoq",
        "routing_class": "sovereign_only",
        "source_generator": "projects/eoq/scripts/generate_scene_pack.py",
        "prompt_id": str(manifest.get("prompt_id") or "").strip() or None,
        "next_action": "materialize_hybrid_acceptance",
    }


def write_project_output_candidate(candidate: dict[str, Any], candidate_root: Path = CANDIDATE_OUTPUT_DIR) -> Path:
    candidate_id = str(candidate.get("candidate_id") or "").strip() or "project-output-candidate"
    path = candidate_root / f"{candidate_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def rebuild_collection_manifest(output_root: Path) -> Path:
    manifests = sorted(output_root.glob("*/manifest.json"))
    lines = [
        "# EOQ Scene Packs",
        "",
        "Generated scene-pack bundles stored under `projects/eoq/NEW/`.",
        "",
        "| Bundle | Scene | Seed | Asset | Prompt ID | Generated At |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for manifest_path in manifests:
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        bundle_dir = manifest_path.parent
        asset_rel = _relative_to_repo(bundle_dir / str(payload.get("asset_filename") or ""))
        lines.append(
            "| "
            + f"`{bundle_dir.name}` | "
            + f"`{payload.get('scene_id')}` | "
            + f"`{payload.get('seed')}` | "
            + f"`{asset_rel}` | "
            + f"`{payload.get('prompt_id')}` | "
            + f"`{payload.get('generated_at')}` |"
        )
    lines.append("")
    manifest_md = output_root / "MANIFEST.md"
    manifest_md.parent.mkdir(parents=True, exist_ok=True)
    manifest_md.write_text("\n".join(lines), encoding="utf-8")
    return manifest_md


def _default_comfyui_url() -> str:
    return (
        os.environ.get("ATHANOR_COMFYUI_URL")
        or os.environ.get("COMFYUI_URL")
        or get_url("comfyui")
    ).rstrip("/")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a reproducible EOQ scene-pack bundle from a pinned ComfyUI workflow.")
    parser.add_argument("--scene-id", required=True)
    parser.add_argument("--scene-name", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--scene-source-ref", default="projects/eoq/src/data/scenes.ts")
    parser.add_argument("--workflow", type=Path, default=DEFAULT_WORKFLOW_PATH)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--comfyui-url", default=_default_comfyui_url())
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--bundle-id")
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument("--json", action="store_true", help="Print the manifest payload after generation.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    workflow_path = args.workflow.resolve()
    output_root = args.output_root.resolve()
    bundle_id = args.bundle_id or f"{_timestamp_slug()}-{_slugify(args.scene_id)}-scene-pack"
    bundle_dir = output_root / bundle_id
    filename_prefix = f"EoBQ/scene/{_slugify(args.scene_id)}"

    workflow = inject_scene_prompt(
        load_workflow(workflow_path),
        prompt=args.prompt,
        seed=args.seed,
        filename_prefix=filename_prefix,
    )
    prompt_id = queue_workflow(args.comfyui_url, workflow, timeout_seconds=args.timeout_seconds)
    file_ref = poll_for_output(
        args.comfyui_url,
        prompt_id,
        timeout_seconds=args.timeout_seconds,
    )
    asset_url = build_view_url(args.comfyui_url, file_ref)
    asset_suffix = Path(file_ref["filename"]).suffix or ".png"
    asset_filename = f"{_slugify(args.scene_id)}-{args.seed}{asset_suffix}"
    asset_path = bundle_dir / asset_filename
    download_asset(asset_url, asset_path, timeout_seconds=args.timeout_seconds)

    manifest = {
        "generated_at": _iso_now(),
        "project_id": "eoq",
        "deliverable_kind": "content_artifact",
        "pack_kind": "scene_pack",
        "bundle_id": bundle_id,
        "scene_id": args.scene_id,
        "scene_name": args.scene_name,
        "scene_source_ref": args.scene_source_ref,
        "workflow_ref": _relative_to_repo(workflow_path),
        "seed": args.seed,
        "prompt": args.prompt,
        "prompt_id": prompt_id,
        "comfyui_url": args.comfyui_url,
        "remote_file_ref": file_ref,
        "asset_filename": asset_filename,
        "asset_ref": _relative_to_repo(asset_path),
        "manifest_ref": _relative_to_repo(bundle_dir / "manifest.json"),
    }
    write_bundle_manifest(bundle_dir / "manifest.json", manifest)
    collection_manifest = rebuild_collection_manifest(output_root)
    manifest["collection_manifest_ref"] = _relative_to_repo(collection_manifest)
    write_bundle_manifest(bundle_dir / "manifest.json", manifest)
    candidate = build_project_output_candidate(manifest)
    candidate_path = write_project_output_candidate(candidate)
    manifest["project_output_candidate_ref"] = _relative_to_repo(candidate_path)
    write_bundle_manifest(bundle_dir / "manifest.json", manifest)

    if args.json:
        print(json.dumps(manifest, indent=2))
    else:
        print(bundle_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
