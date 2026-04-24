from __future__ import annotations

import importlib.util
import json
import sys
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "projects" / "eoq" / "scripts" / "generate_scene_pack.py"


def _load_module():
    name = f"generate_eoq_scene_pack_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_inject_scene_prompt_updates_prompt_seed_and_prefix() -> None:
    module = _load_module()
    workflow = {
        "3": {"inputs": {"text": "old prompt"}},
        "7": {"inputs": {"seed": 123}},
        "10": {"inputs": {"filename_prefix": "EoBQ/scene"}},
    }

    result = module.inject_scene_prompt(
        workflow,
        prompt="new prompt",
        seed=777,
        filename_prefix="EoBQ/scene/courtyard",
    )

    assert workflow["3"]["inputs"]["text"] == "old prompt"
    assert result["3"]["inputs"]["text"] == "new prompt"
    assert result["7"]["inputs"]["seed"] == 777
    assert result["10"]["inputs"]["filename_prefix"] == "EoBQ/scene/courtyard"


def test_rebuild_collection_manifest_lists_generated_scene_pack(tmp_path: Path) -> None:
    module = _load_module()
    output_root = tmp_path / "NEW"
    bundle_dir = output_root / "20260420T193200Z-courtyard-scene-pack"
    bundle_dir.mkdir(parents=True)
    (bundle_dir / "manifest.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-20T19:32:00+00:00",
                "scene_id": "courtyard",
                "seed": 20260420,
                "prompt_id": "prompt-123",
                "asset_filename": "courtyard-20260420.png",
            }
        ),
        encoding="utf-8",
    )
    (bundle_dir / "courtyard-20260420.png").write_bytes(b"fake")

    manifest_path = module.rebuild_collection_manifest(output_root)
    rendered = manifest_path.read_text(encoding="utf-8")

    assert manifest_path == output_root / "MANIFEST.md"
    assert "`20260420T193200Z-courtyard-scene-pack`" in rendered
    assert "`courtyard`" in rendered
    assert "`20260420`" in rendered
    assert "`prompt-123`" in rendered


def test_build_project_output_candidate_uses_manifest_refs_for_pending_acceptance() -> None:
    module = _load_module()
    manifest = {
        "generated_at": "2026-04-20T19:32:00+00:00",
        "project_id": "eoq",
        "bundle_id": "courtyard-scene-pack-alpha",
        "scene_name": "The Courtyard of Ashenmoor",
        "deliverable_kind": "content_artifact",
        "asset_ref": "projects/eoq/NEW/courtyard-scene-pack-alpha/courtyard-20260420.png",
        "manifest_ref": "projects/eoq/NEW/courtyard-scene-pack-alpha/manifest.json",
        "collection_manifest_ref": "projects/eoq/NEW/MANIFEST.md",
        "workflow_ref": "projects/eoq/comfyui/flux-scene.json",
        "prompt_id": "prompt-123",
    }

    candidate = module.build_project_output_candidate(manifest)

    assert candidate["candidate_id"] == "eoq-courtyard-scene-pack-alpha"
    assert candidate["project_id"] == "eoq"
    assert candidate["approval_posture"] == "hybrid"
    assert candidate["acceptance_state"] == "pending_materialization"
    assert "projects/eoq/NEW/courtyard-scene-pack-alpha/manifest.json" in candidate["deliverable_refs"]
    assert candidate["workflow_refs"] == ["projects/eoq/comfyui/flux-scene.json"]


def test_default_comfyui_url_resolves_from_topology(monkeypatch) -> None:
    module = _load_module()
    monkeypatch.delenv("ATHANOR_COMFYUI_URL", raising=False)
    monkeypatch.delenv("COMFYUI_URL", raising=False)

    assert module._default_comfyui_url() == module.get_url("comfyui").rstrip("/")
