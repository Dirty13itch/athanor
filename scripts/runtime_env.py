from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


DEFAULT_RUNTIME_ENV_PATH = Path.home() / ".athanor" / "runtime.env"
FALLBACK_LITELLM_API_BASE = "http://192.168.1.203:4000/v1"


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


def _first_env_value(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def _default_litellm_api_base() -> str:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    try:
        from services.cluster_config import get_url

        return _normalize_litellm_api_base(get_url("litellm"))
    except Exception:
        return FALLBACK_LITELLM_API_BASE


def _normalize_litellm_api_base(value: str) -> str:
    raw = str(value).strip()
    if not raw:
        return ""

    candidate = raw
    if "://" not in candidate:
        candidate = f"http://{candidate}"

    parsed = urlsplit(candidate)
    scheme = parsed.scheme or "http"
    netloc = parsed.netloc or parsed.path
    path = parsed.path if parsed.netloc else ""
    normalized_path = path.rstrip("/")

    if normalized_path.endswith("/chat/completions"):
        normalized_path = normalized_path[: -len("/chat/completions")]
    if not normalized_path:
        normalized_path = "/v1"
    elif not normalized_path.endswith("/v1"):
        normalized_path = f"{normalized_path}/v1"

    return urlunsplit((scheme, netloc, normalized_path, "", "")).rstrip("/")


def _openai_host_and_base_path(api_base: str) -> tuple[str, str]:
    normalized = _normalize_litellm_api_base(api_base)
    parsed = urlsplit(normalized)
    host = urlunsplit((parsed.scheme or "http", parsed.netloc or parsed.path, "", "", "")).rstrip("/")
    path = parsed.path.strip("/") or "v1"
    return host, f"{path}/chat/completions"


def _derived_runtime_contract() -> dict[str, str]:
    resolved: dict[str, str] = {}

    gateway_key = _first_env_value("ATHANOR_LITELLM_API_KEY", "LITELLM_API_KEY", "LITELLM_MASTER_KEY")
    if gateway_key:
        resolved["ATHANOR_LITELLM_API_KEY"] = gateway_key
        resolved["LITELLM_API_KEY"] = _first_env_value("LITELLM_API_KEY") or gateway_key
        resolved["OPENAI_API_KEY"] = _first_env_value("OPENAI_API_KEY") or gateway_key

    gateway_url = _first_env_value("ATHANOR_LITELLM_URL", "LITELLM_URL", "OPENAI_API_BASE")
    if not gateway_url:
        openai_host = _first_env_value("OPENAI_HOST")
        openai_base_path = _first_env_value("OPENAI_BASE_PATH")
        if openai_host:
            base_path = openai_base_path.strip().strip("/")
            if base_path.endswith("chat/completions"):
                base_path = base_path[: -len("chat/completions")].rstrip("/")
            gateway_url = f"{openai_host.rstrip('/')}/{base_path or 'v1'}"

    if not gateway_url:
        gateway_url = _default_litellm_api_base()

    api_base = _normalize_litellm_api_base(gateway_url)
    if api_base:
        openai_host, openai_base_path = _openai_host_and_base_path(api_base)
        resolved["ATHANOR_LITELLM_URL"] = api_base
        resolved["LITELLM_URL"] = _first_env_value("LITELLM_URL") or api_base
        resolved["OPENAI_API_BASE"] = _first_env_value("OPENAI_API_BASE") or api_base
        resolved["OPENAI_HOST"] = _first_env_value("OPENAI_HOST") or openai_host
        resolved["OPENAI_BASE_PATH"] = _first_env_value("OPENAI_BASE_PATH") or openai_base_path

    return resolved


def load_runtime_env_contract(*, env_names: list[str] | None = None) -> dict[str, str]:
    load_optional_runtime_env()
    derived = _derived_runtime_contract()
    requested = [name for name in (env_names or []) if str(name).strip()]

    for name, value in derived.items():
        if value and (name not in os.environ or not os.environ[name].strip()):
            os.environ[name] = value

    if not requested:
        return {name: value for name, value in derived.items() if value}
    return {
        name: os.environ.get(name, "").strip()
        for name in requested
        if os.environ.get(name, "").strip()
    }


def runtime_env_status(*, env_names: list[str] | None = None) -> dict[str, object]:
    requested = [name for name in (env_names or []) if str(name).strip()]
    path_used = load_optional_runtime_env(env_names=requested)
    direct = sorted(name for name in requested if os.environ.get(name, "").strip())
    load_runtime_env_contract(env_names=requested)
    candidates = _candidate_paths()
    resolved = sorted(name for name in requested if os.environ.get(name, "").strip())
    missing = sorted(name for name in requested if name not in resolved)
    derived = sorted(name for name in resolved if name not in direct)
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
        "derived": derived,
    }


def _render_resolved_values(values: dict[str, str], output_format: str) -> str:
    if output_format == "dotenv":
        return "\n".join(f"{key}={value}" for key, value in values.items())
    if output_format == "powershell":
        lines: list[str] = []
        for key, value in values.items():
            escaped = value.replace("'", "''")
            lines.append(f"$env:{key}='{escaped}'")
        return "\n".join(lines)
    return json.dumps(values, indent=2, sort_keys=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect the managed Athanor runtime env surface.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--check",
        nargs="+",
        metavar="ENV_NAME",
        help="Env vars that must resolve from the current shell or managed runtime env file.",
    )
    group.add_argument(
        "--resolve",
        nargs="+",
        metavar="ENV_NAME",
        help="Resolve and print concrete env values for launcher wrappers.",
    )
    parser.add_argument(
        "--format",
        choices=["json", "dotenv", "powershell"],
        default="json",
        help="Output format for --resolve.",
    )
    args = parser.parse_args()

    if args.resolve:
        resolved_values = load_runtime_env_contract(env_names=args.resolve)
        print(_render_resolved_values(resolved_values, args.format))
        missing = [name for name in args.resolve if not resolved_values.get(name, "").strip()]
        return 1 if missing else 0

    status = runtime_env_status(env_names=args.check or [])
    print(json.dumps(status, indent=2, sort_keys=True))
    if args.check and status["missing"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
