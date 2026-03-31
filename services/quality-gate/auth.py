from __future__ import annotations

import os
from dataclasses import dataclass
from secrets import compare_digest
from typing import Final

from fastapi import Request
from fastapi.responses import JSONResponse

DEV_LIKE_ENVIRONMENTS: Final[frozenset[str]] = frozenset(
    {"dev", "development", "local", "fixture", "test", "testing", "ci"}
)

DEFAULT_AUTH_EXEMPT_PATHS: Final[frozenset[str]] = frozenset(
    {"/health", "/docs", "/openapi.json", "/redoc"}
)

DEFAULT_ENVIRONMENT_VARS: Final[tuple[str, ...]] = (
    "QUALITY_GATE_ENV",
    "ATHANOR_ENV",
    "ATHANOR_RUNTIME_ENV",
    "APP_ENV",
    "ENVIRONMENT",
)

DEFAULT_TOKEN_VARS: Final[tuple[str, ...]] = (
    "QUALITY_GATE_API_TOKEN",
    "ATHANOR_QUALITY_GATE_API_TOKEN",
    "ATHANOR_AGENT_API_TOKEN",
    "ATHANOR_API_BEARER_TOKEN",
)


def normalize_environment(value: str | None) -> str:
    return (value or "").strip().lower()


def is_dev_like_environment(value: str | None) -> bool:
    return normalize_environment(value) in DEV_LIKE_ENVIRONMENTS


def first_nonempty_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


@dataclass(frozen=True, slots=True)
class BearerAuthContract:
    service_name: str
    runtime_environment: str
    bearer_token: str
    token_env_names: tuple[str, ...]
    exempt_paths: frozenset[str] = DEFAULT_AUTH_EXEMPT_PATHS

    @property
    def auth_enabled(self) -> bool:
        return not is_dev_like_environment(self.runtime_environment) and bool(self.bearer_token.strip())

    def validate_startup(self) -> None:
        if self.auth_enabled or is_dev_like_environment(self.runtime_environment):
            return

        token_names = ", ".join(self.token_env_names) if self.token_env_names else "<unset>"
        raise RuntimeError(
            f"{self.service_name} requires a bearer token outside dev-like environments. "
            f"Set one of: {token_names}."
        )

    def authorize(self, request: Request) -> JSONResponse | None:
        if request.url.path in self.exempt_paths or is_dev_like_environment(self.runtime_environment):
            return None

        expected = self.bearer_token.strip()
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer ") and compare_digest(auth.removeprefix("Bearer ").strip(), expected):
            return None

        return JSONResponse(
            status_code=401,
            content={"error": {"message": "Invalid or missing bearer token", "type": "authentication_error"}},
        )


def build_contract(
    *,
    service_name: str,
    environment_env_names: tuple[str, ...] = DEFAULT_ENVIRONMENT_VARS,
    token_env_names: tuple[str, ...] = DEFAULT_TOKEN_VARS,
    exempt_paths: frozenset[str] = DEFAULT_AUTH_EXEMPT_PATHS,
) -> BearerAuthContract:
    return BearerAuthContract(
        service_name=service_name,
        runtime_environment=first_nonempty_env(*environment_env_names) or "production",
        bearer_token=first_nonempty_env(*token_env_names),
        token_env_names=token_env_names,
        exempt_paths=exempt_paths,
    )
