from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


DEFAULT_RUNTIME_ENV_PATH = Path.home() / ".athanor" / "runtime.env"


def _candidate_paths() -> list[Path]:
    candidates: list[Path] = []
    override = os.environ.get("ATHANOR_RUNTIME_ENV_FILE", "").strip()
    if override:
        candidates.append(Path(os.path.expanduser(override)))
    candidates.append(DEFAULT_RUNTIME_ENV_PATH)
    seen: set[Path] = set()
    ordered: list[Path] = []
    for candidate in candidates:
        if candidate in seen:
            continue
        ordered.append(candidate)
        seen.add(candidate)
    return ordered


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[len("export ") :].strip()
    if "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return key, value


def load_optional_runtime_env(*, env_names: list[str] | None = None) -> str | None:
    requested = {name for name in (env_names or []) if str(name).strip()}
    for path in _candidate_paths():
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            parsed = _parse_env_line(raw_line)
            if parsed is None:
                continue
            key, value = parsed
            if requested and key not in requested:
                continue
            if key not in os.environ or not os.environ[key].strip():
                os.environ[key] = value
        return str(path)
    return None


def runtime_env_status(*, env_names: list[str] | None = None) -> dict[str, object]:
    requested = [name for name in (env_names or []) if str(name).strip()]
    path_used = load_optional_runtime_env(env_names=requested)
    candidates = _candidate_paths()
    resolved = sorted(name for name in requested if os.environ.get(name, "").strip())
    missing = sorted(name for name in requested if name not in resolved)
    return {
        "path_used": path_used,
        "candidates": [
            {
                "path": str(path),
                "exists": path.exists(),
            }
            for path in candidates
        ],
        "resolved": resolved,
        "missing": missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect the managed Athanor runtime env surface.")
    parser.add_argument(
        "--check",
        nargs="+",
        metavar="ENV_NAME",
        help="Env vars that must resolve from the current shell or managed runtime env file.",
    )
    args = parser.parse_args()

    status = runtime_env_status(env_names=args.check or [])
    print(json.dumps(status, indent=2, sort_keys=True))
    if args.check and status["missing"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
