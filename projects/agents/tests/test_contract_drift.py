import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
AGENT_SRC_ROOT = REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents"

SECRET_PATTERNS = [
    re.compile("sk-" + "athanor", re.IGNORECASE),
    re.compile("athanor" + "2026", re.IGNORECASE),
    re.compile("Hockey" + "1298", re.IGNORECASE),
    re.compile("Will2" + "live!", re.IGNORECASE),
    re.compile("Jv1Vg9HAML2j" + "HGWjFnTCcIsqSzqZfIQz", re.IGNORECASE),
]
RAW_IP_PATTERN = re.compile(r"192\.168\.1\.\d+")

ALLOWED_AGENT_IP_FILES = {
    AGENT_SRC_ROOT / "config.py",
}

SECRET_SCAN_ROOTS = [
    REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents",
    REPO_ROOT / "projects" / "agents" / "docker-compose.yml",
    REPO_ROOT / "projects" / "agents" / ".env.example",
    REPO_ROOT / "ansible" / "roles" / "agents",
    REPO_ROOT / "ansible" / "roles" / "dashboard",
    REPO_ROOT / "ansible" / "roles" / "eoq",
    REPO_ROOT / "ansible" / "roles" / "ulrich-energy",
    REPO_ROOT / "ansible" / "roles" / "vault-langfuse",
    REPO_ROOT / "ansible" / "roles" / "vault-litellm",
    REPO_ROOT / "ansible" / "roles" / "vault-miniflux",
    REPO_ROOT / "ansible" / "roles" / "vault-neo4j",
    REPO_ROOT / "ansible" / "roles" / "vault-open-webui",
]


def iter_text_files(root: Path):
    if root.is_file():
        yield root
        return

    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if any(part in {".next", "node_modules", ".venv", "__pycache__"} for part in path.parts):
            continue
        if path.suffix.lower() in {
            ".py",
            ".yml",
            ".yaml",
            ".j2",
            ".md",
            ".toml",
            ".env",
            ".example",
            ".txt",
        } or path.name in {"docker-compose.yml"}:
            yield path


class ContractDriftTest(unittest.TestCase):
    def test_no_secret_literals_remain_in_managed_runtime_scopes(self) -> None:
        violations: list[str] = []

        for root in SECRET_SCAN_ROOTS:
            for path in iter_text_files(root):
                text = path.read_text(encoding="utf-8", errors="ignore")
                for pattern in SECRET_PATTERNS:
                    if pattern.search(text):
                        violations.append(str(path.relative_to(REPO_ROOT)))
                        break

        self.assertEqual([], violations, f"Secret literals remain in managed scopes: {violations}")

    def test_agent_source_uses_centralized_topology_only(self) -> None:
        violations: list[str] = []

        for path in iter_text_files(AGENT_SRC_ROOT):
            if path in ALLOWED_AGENT_IP_FILES:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if RAW_IP_PATTERN.search(text):
                violations.append(str(path.relative_to(REPO_ROOT)))

        self.assertEqual([], violations, f"Raw cluster IPs remain outside config.py: {violations}")


if __name__ == "__main__":
    unittest.main()
