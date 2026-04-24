from __future__ import annotations

import importlib.util
import sys
import uuid
from pathlib import Path
import sys


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


def test_newline_style_preserves_existing_crlf_file(tmp_path: Path) -> None:
    module = _load_module(
        f"generate_project_maturity_report_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_project_maturity_report.py",
    )

    output_path = tmp_path / "PROJECT-MATURITY-REPORT.md"
    output_path.write_bytes(b"# Report\r\n\r\nBody\r\n")
    module.tracked_newline_style = lambda path: None

    assert module.newline_style(output_path) == "\r\n"


def test_rendered_output_can_be_normalized_to_existing_newline_style() -> None:
    module = _load_module(
        f"generate_project_maturity_report_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_project_maturity_report.py",
    )

    portfolio = {
        "version": "2026-03-27.1",
        "classes": [{"id": "platform-core", "requirements": []}],
        "projects": [{"id": "agents", "label": "Athanor Agents", "class": "platform-core"}],
    }
    topology = {"services": []}

    rendered = module.render_project_maturity_report(portfolio, topology).replace("\n", "\r\n")

    assert "\r\n" in rendered
    assert rendered.endswith("\r\n")


def test_newline_style_prefers_tracked_head_style_over_dirty_workspace_style(tmp_path: Path) -> None:
    module = _load_module(
        f"generate_project_maturity_report_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_project_maturity_report.py",
    )

    output_path = tmp_path / "PROJECT-MATURITY-REPORT.md"
    output_path.write_text("# Report\n\nBody\n", encoding="utf-8")
    module.tracked_newline_style = lambda path: "\r\n"

    assert module.newline_style(output_path) == "\r\n"


def test_check_mode_treats_matching_crlf_output_as_fresh(tmp_path: Path, monkeypatch) -> None:
    module = _load_module(
        f"generate_project_maturity_report_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_project_maturity_report.py",
    )

    output_path = tmp_path / "PROJECT-MATURITY-REPORT.md"
    portfolio_path = tmp_path / "project-maturity-registry.json"
    topology_path = tmp_path / "platform-topology.json"

    portfolio = {
        "version": "2026-03-27.1",
        "classes": [{"id": "platform-core", "requirements": []}],
        "projects": [{"id": "agents", "label": "Athanor Agents", "class": "platform-core"}],
    }
    topology = {"services": []}

    portfolio_path.write_text(__import__("json").dumps(portfolio), encoding="utf-8")
    topology_path.write_text(__import__("json").dumps(topology), encoding="utf-8")

    module.PORTFOLIO_PATH = portfolio_path
    module.TOPOLOGY_PATH = topology_path
    module.OUTPUT_PATH = output_path
    module.tracked_newline_style = lambda path: "\r\n"

    rendered = module.render_project_maturity_report(portfolio, topology).replace("\n", "\r\n")
    output_path.write_bytes(rendered.encode("utf-8"))

    monkeypatch.setattr(sys, "argv", ["generate_project_maturity_report.py", "--check"])
    assert module.main() == 0
