from __future__ import annotations

import importlib.util
import sys
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_build_payload_filters_to_ready_for_approval_packets() -> None:
    module = _load_module(
        f"write_runtime_packet_inbox_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_runtime_packet_inbox.py",
    )

    module.load_runtime_packets = lambda: {
        "packets": [
            {
                "id": "dev-runtime-ssh-access-recovery-packet",
                "label": "DEV Runtime SSH Access Recovery",
                "status": "ready_for_approval",
                "lane_id": "runtime_ownership",
                "host": "DEV",
                "approval_packet_type": "runtime_reconfiguration",
                "goal": "Restore governed SSH reachability.",
                "preflight_commands": ["ssh dev true"],
                "verification_commands": ["ssh dev hostname"],
                "rollback_steps": ["Revert SSH config change."],
                "exact_steps": ["Approve and apply bounded SSH repair."],
            },
            {
                "id": "already-done",
                "label": "Already Done",
                "status": "completed",
            },
        ]
    }

    payload = module.build_payload()

    assert payload["packet_count"] == 1
    assert payload["packets"][0]["id"] == "dev-runtime-ssh-access-recovery-packet"
    assert payload["packets"][0]["approval_type"] == "runtime_reconfiguration"
    assert payload["packets"][0]["next_operator_action"] == "Approve and apply bounded SSH repair."
