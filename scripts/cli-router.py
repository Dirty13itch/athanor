#!/usr/bin/env python3
"""
Athanor CLI Router — Intelligent task->subscription CLI matching.
================================================================
Routes tasks to the best subscription CLI based on task type, available
quota, and learned performance. Imported by Subscription Burn.

Classification approach (zero cloud spend):
  1. Embedding similarity via local qwen3-embed-8b (~10ms)
  2. Fallback: local Qwen3.5 via LiteLLM for ambiguous tasks (~200ms)

Learning loop:
  - Records outcome per cli x task_type in ~/.athanor/cli-router-history.json
  - After 50+ samples, win-rate adjusts routing weights

Author: Athanor autonomous system
"""


import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import httpx
import numpy as np
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
REPO_ROOT = SCRIPT_DIR.parent

from fastapi import Request
from fastapi.responses import JSONResponse

from operator_contract import (
    build_operator_action,
    emit_operator_audit_event,
    require_operator_action,
)

try:
    from scripts._cluster_config import LITELLM_KEY, get_url
except ModuleNotFoundError:
    from _cluster_config import LITELLM_KEY, get_url

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

DEFAULT_TIMEZONE = os.environ.get("ATHANOR_TIMEZONE", "America/Chicago")
TZ = ZoneInfo(DEFAULT_TIMEZONE)

log = logging.getLogger("cli-router")
SERVICE_NAME = "subscription-burn"
POLICY_PATH = REPO_ROOT / "projects" / "agents" / "config" / "subscription-routing-policy.yaml"
PROVIDER_CATALOG_PATH = REPO_ROOT / "config" / "automation-backbone" / "provider-catalog.json"

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
EMBEDDING_URL = f"{get_url('embedding')}/v1/embeddings"
EMBEDDING_MODEL = "qwen3-embed-8b"
LITELLM_URL = get_url("litellm")
SUBSCRIPTION_BURN_URL = get_url("subscription_burn")
# LITELLM_KEY imported from cluster_config
LITELLM_MODEL = "creative"  # Qwen3.5 on WORKSHOP

HISTORY_FILE = Path.home() / ".athanor" / "cli-router-history.json"
EMBEDDINGS_CACHE = Path.home() / ".athanor" / "cli-router-embeddings.npz"

# Minimum samples before learned weights override static rules
MIN_SAMPLES_FOR_LEARNING = 50
# Similarity threshold below which we fall back to LLM classification
SIMILARITY_THRESHOLD = 0.45

# ---------------------------------------------------------------------------
# Task type definitions with representative utterances for embedding matching.
# Task classification stays local, but provider order now derives from the
# canonical subscription routing policy and provider catalog.
# ---------------------------------------------------------------------------
TASK_TYPE_UTTERANCES: dict[str, list[str]] = {
    "architecture": [
        "design the system architecture",
        "restructure the service layer",
        "plan the migration strategy",
        "architect a new module for the cluster",
        "design data flow between services",
        "create architecture decision record",
    ],
    "code_review": [
        "review this pull request",
        "check this code for issues",
        "audit the implementation quality",
        "review changes across multiple files",
        "inspect code for anti-patterns",
        "peer review the refactored module",
    ],
    "feature_dev": [
        "implement the new feature",
        "build the API endpoint",
        "add a new component to the UI",
        "create a new service module",
        "develop the integration with the external API",
        "write the feature from the spec",
    ],
    "debugging": [
        "fix this bug",
        "debug the failing test",
        "trace the error in production logs",
        "find why the service is crashing",
        "diagnose the memory leak",
        "troubleshoot the connection timeout",
    ],
    "refactoring": [
        "refactor the module for clarity",
        "extract shared utilities into a common package",
        "reduce code duplication across services",
        "simplify the class hierarchy",
        "clean up legacy patterns",
        "restructure imports and dependencies",
    ],
    "testing": [
        "write unit tests for the module",
        "add integration tests for the API",
        "create test fixtures and mocks",
        "improve test coverage",
        "write end-to-end tests",
        "add property-based tests",
    ],
    "documentation": [
        "write API documentation",
        "document the deployment process",
        "generate docstrings for the module",
        "create a runbook for operations",
        "write the README for the project",
        "document configuration options",
    ],
    "research": [
        "research alternatives for the database",
        "compare framework options",
        "survey available tools for monitoring",
        "investigate best practices for caching",
        "benchmark different approaches",
        "find the best library for the task",
    ],
    "fact_check": [
        "verify the accuracy of the documentation",
        "check if the API spec matches the implementation",
        "validate configuration values",
        "confirm compatibility between versions",
        "cross-reference the dependency versions",
    ],
    "deep_research": [
        "deep research on distributed consensus algorithms",
        "synthesize information from multiple sources about GPU scheduling",
        "comprehensive analysis with citations on container orchestration",
        "multi-source investigation with references",
        "in-depth study with source attribution",
    ],
}

TASK_TYPE_EXECUTION_PROFILES: dict[str, dict[str, Any]] = {
    "architecture": {
        "requester": "coding-agent",
        "task_class": "interactive_architecture",
        "interactive": True,
        "priority": "high",
        "sensitivity": "repo_internal",
    },
    "code_review": {
        "requester": "coding-agent",
        "task_class": "interactive_architecture",
        "interactive": True,
        "priority": "high",
        "sensitivity": "repo_internal",
    },
    "feature_dev": {
        "requester": "coding-agent",
        "task_class": "multi_file_implementation",
        "interactive": False,
        "priority": "normal",
        "sensitivity": "repo_internal",
    },
    "debugging": {
        "requester": "coding-agent",
        "task_class": "multi_file_implementation",
        "interactive": False,
        "priority": "high",
        "sensitivity": "repo_internal",
    },
    "refactoring": {
        "requester": "coding-agent",
        "task_class": "multi_file_implementation",
        "interactive": False,
        "priority": "normal",
        "sensitivity": "repo_internal",
    },
    "testing": {
        "requester": "coding-agent",
        "task_class": "async_backlog_execution",
        "interactive": False,
        "priority": "normal",
        "sensitivity": "repo_internal",
    },
    "documentation": {
        "requester": "research-agent",
        "task_class": "search_heavy_planning",
        "interactive": False,
        "priority": "normal",
        "sensitivity": "mixed",
    },
    "research": {
        "requester": "research-agent",
        "task_class": "search_heavy_planning",
        "interactive": False,
        "priority": "normal",
        "sensitivity": "mixed",
    },
    "fact_check": {
        "requester": "research-agent",
        "task_class": "repo_wide_audit",
        "interactive": False,
        "priority": "normal",
        "sensitivity": "mixed",
    },
    "deep_research": {
        "requester": "research-agent",
        "task_class": "repo_wide_audit",
        "interactive": False,
        "priority": "high",
        "sensitivity": "mixed",
    },
}

ALL_TASK_TYPES = list(TASK_TYPE_EXECUTION_PROFILES.keys())

_POLICY_CACHE: dict[str, Any] | None = None
_POLICY_CACHE_MTIME_NS: int | None = None
_PROVIDER_SNAPSHOT_CACHE: dict[str, Any] | None = None
_PROVIDER_SNAPSHOT_MTIME_NS: int | None = None


def _load_policy() -> dict[str, Any]:
    global _POLICY_CACHE
    global _POLICY_CACHE_MTIME_NS

    if not POLICY_PATH.exists():
        return {"providers": {}, "task_classes": {}, "agents": {}}

    stat = POLICY_PATH.stat()
    if _POLICY_CACHE is not None and _POLICY_CACHE_MTIME_NS == stat.st_mtime_ns:
        return _POLICY_CACHE

    with POLICY_PATH.open("r", encoding="utf-8") as handle:
        policy = yaml.safe_load(handle) or {}
    if not isinstance(policy, dict):
        raise ValueError(f"Subscription policy at {POLICY_PATH} must be a mapping")
    policy.setdefault("providers", {})
    policy.setdefault("task_classes", {})
    policy.setdefault("agents", {})
    _POLICY_CACHE = policy
    _POLICY_CACHE_MTIME_NS = stat.st_mtime_ns
    return policy


def _provider_catalog_snapshot() -> dict[str, Any]:
    global _PROVIDER_SNAPSHOT_CACHE
    global _PROVIDER_SNAPSHOT_MTIME_NS

    if not PROVIDER_CATALOG_PATH.exists():
        return {"providers": []}

    stat = PROVIDER_CATALOG_PATH.stat()
    if _PROVIDER_SNAPSHOT_CACHE is not None and _PROVIDER_SNAPSHOT_MTIME_NS == stat.st_mtime_ns:
        return _PROVIDER_SNAPSHOT_CACHE

    try:
        payload = json.loads(PROVIDER_CATALOG_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("Failed to load provider catalog from %s: %s", PROVIDER_CATALOG_PATH, exc)
        payload = {"providers": []}

    allowed = {str(item) for item in dict(_load_policy().get("providers") or {}).keys()}
    snapshot = {
        "providers": [
            entry
            for entry in payload.get("providers", [])
            if isinstance(entry, dict) and str(entry.get("id") or "") in allowed
        ]
    }
    _PROVIDER_SNAPSHOT_CACHE = snapshot
    _PROVIDER_SNAPSHOT_MTIME_NS = stat.st_mtime_ns
    return snapshot


def _provider_catalog_index() -> dict[str, dict[str, Any]]:
    return {
        str(entry.get("id") or ""): dict(entry)
        for entry in _provider_catalog_snapshot().get("providers", [])
        if isinstance(entry, dict) and str(entry.get("id") or "").strip()
    }


def _provider_cli_name(provider_id: str, catalog_index: dict[str, dict[str, Any]] | None = None) -> str:
    provider = (catalog_index or _provider_catalog_index()).get(provider_id, {})
    commands = provider.get("cli_commands", [])
    if isinstance(commands, list):
        for command in commands:
            alias = str(command or "").strip()
            if alias:
                return alias
    return ""


def _task_profile(task_type: str) -> dict[str, Any]:
    return dict(
        TASK_TYPE_EXECUTION_PROFILES.get(
            task_type,
            {
                "requester": "coding-agent",
                "task_class": "multi_file_implementation",
                "interactive": False,
                "priority": "normal",
                "sensitivity": "repo_internal",
            },
        )
    )


def _canonical_cli_candidates(task_type: str, task_description: str) -> list[tuple[str, str]]:
    profile = _task_profile(task_type)
    policy = _load_policy()
    task_class = str(profile.get("task_class") or "multi_file_implementation")
    task_meta = dict(policy.get("task_classes", {}).get(task_class, {}) or {})
    ordered_provider_ids = [
        str(item or "")
        for item in list(task_meta.get("primary", [])) + list(task_meta.get("fallback", []))
    ]
    policy_providers = dict(policy.get("providers") or {})
    catalog_index = _provider_catalog_index()
    resolved: list[tuple[str, str]] = []
    seen_provider: set[str] = set()
    seen_cli: set[str] = set()

    for provider_id in ordered_provider_ids:
        if not provider_id or provider_id in seen_provider:
            continue
        provider_meta = dict(policy_providers.get(provider_id) or {})
        if not provider_meta.get("enabled", True):
            continue
        if str(provider_meta.get("routing_posture") or "") != "ordinary_auto":
            continue
        catalog_entry = catalog_index.get(provider_id, {})
        if str(catalog_entry.get("access_mode") or "") != "cli":
            continue
        cli_name = _provider_cli_name(provider_id, catalog_index)
        if not cli_name or cli_name in seen_cli:
            continue
        resolved.append((provider_id, cli_name))
        seen_provider.add(provider_id)
        seen_cli.add(cli_name)

    return resolved


def _known_cli_aliases() -> list[str]:
    aliases: list[str] = []
    seen: set[str] = set()
    for task_type, utterances in TASK_TYPE_UTTERANCES.items():
        sample = utterances[0] if utterances else task_type
        for _, cli_name in _canonical_cli_candidates(task_type, sample):
            if cli_name in seen:
                continue
            aliases.append(cli_name)
            seen.add(cli_name)
    return aliases


def _operator_action_payload(body: dict[str, Any]) -> dict[str, Any]:
    payload = body.get("operator_action")
    if isinstance(payload, dict):
        return dict(payload)
    return body


async def _load_operator_body(
    request: Request,
    *,
    route: str,
    action_class: str,
    default_reason: str,
):
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    if not isinstance(body, dict):
        body = {}

    payload = _operator_action_payload(body)
    candidate = build_operator_action(payload, default_reason=default_reason)
    try:
        action = require_operator_action(payload, action_class=action_class, default_reason=default_reason)
    except Exception as exc:
        detail = getattr(exc, "detail", str(exc))
        status_code = getattr(exc, "status_code", 400)
        await emit_operator_audit_event(
            service=SERVICE_NAME,
            route=route,
            action_class=action_class,
            decision="denied",
            status_code=status_code,
            action=candidate,
            detail=str(detail),
        )
        return None, None, JSONResponse(status_code=status_code, content={"error": detail})

    return body, action, None


# ---------------------------------------------------------------------------
# Embedding cache -- pre-computed centroids per task type
# ---------------------------------------------------------------------------
@dataclass
class EmbeddingIndex:
    """Stores centroid embeddings for each task type for fast similarity lookup."""

    centroids: dict[str, np.ndarray] = field(default_factory=dict)
    dim: int = 0
    ready: bool = False

    def similarity(self, query_vec: np.ndarray) -> list[tuple[str, float]]:
        """Return task types ranked by cosine similarity to query_vec."""
        if not self.ready:
            return []
        scores = []
        for task_type, centroid in self.centroids.items():
            sim = float(np.dot(query_vec, centroid) / (
                np.linalg.norm(query_vec) * np.linalg.norm(centroid) + 1e-9
            ))
            scores.append((task_type, sim))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores


# ---------------------------------------------------------------------------
# History tracker -- learned performance per cli x task_type
# ---------------------------------------------------------------------------
@dataclass
class RoutingHistory:
    """Tracks success/failure per cli x task_type for learned routing."""

    records: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)
    # Structure: {cli: {task_type: {"wins": int, "losses": int,
    #                                "total_duration": float, "count": int}}}

    @classmethod
    def load(cls) -> "RoutingHistory":
        h = cls()
        if HISTORY_FILE.exists():
            try:
                data = json.loads(HISTORY_FILE.read_text())
                h.records = data.get("records", {})
            except Exception as e:
                log.warning(f"Failed to load routing history: {e}")
        return h

    def save(self):
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        HISTORY_FILE.write_text(json.dumps({
            "records": self.records,
            "updated_at": datetime.now(TZ).isoformat(),
        }, indent=2))

    def record(self, cli: str, task_type: str, success: bool, duration: float):
        if cli not in self.records:
            self.records[cli] = {}
        if task_type not in self.records[cli]:
            self.records[cli][task_type] = {
                "wins": 0, "losses": 0, "total_duration": 0.0, "count": 0,
            }
        entry = self.records[cli][task_type]
        if success:
            entry["wins"] += 1
        else:
            entry["losses"] += 1
        entry["total_duration"] += duration
        entry["count"] += 1
        self.save()

    def win_rate(self, cli: str, task_type: str) -> float | None:
        """Return win rate if enough samples, else None."""
        entry = self.records.get(cli, {}).get(task_type)
        if not entry or entry["count"] < MIN_SAMPLES_FOR_LEARNING:
            return None
        total = entry["wins"] + entry["losses"]
        if total == 0:
            return None
        return entry["wins"] / total

    def avg_duration(self, cli: str, task_type: str) -> float | None:
        entry = self.records.get(cli, {}).get(task_type)
        if not entry or entry["count"] == 0:
            return None
        return entry["total_duration"] / entry["count"]

    def sample_count(self, cli: str, task_type: str) -> int:
        entry = self.records.get(cli, {}).get(task_type)
        if not entry:
            return 0
        return entry["count"]

    def summary(self) -> dict[str, Any]:
        """Return a summary suitable for API responses."""
        out: dict[str, Any] = {}
        for cli, task_types in self.records.items():
            out[cli] = {}
            for tt, stats in task_types.items():
                total = stats["wins"] + stats["losses"]
                out[cli][tt] = {
                    "win_rate": round(stats["wins"] / total, 3) if total else 0,
                    "count": stats["count"],
                    "avg_duration_s": round(
                        stats["total_duration"] / stats["count"], 1
                    ) if stats["count"] else 0,
                }
        return out


# ---------------------------------------------------------------------------
# CLIRouter -- main routing engine
# ---------------------------------------------------------------------------
class CLIRouter:
    """Routes tasks to the best subscription CLI based on task type and quota.

    Imported by Subscription Burn to enhance mechanical scheduling with
    intelligent task->CLI matching.
    """

    def __init__(self):
        self.index = EmbeddingIndex()
        self.history = RoutingHistory.load()
        self._http: httpx.AsyncClient | None = None
        self._available_clis: dict[str, bool] = {}
        self._cli_to_subscription: dict[str, str] = {}
        self._cli_to_provider: dict[str, str] = {}
        self._last_availability_check: float = 0
        self._availability_ttl: float = 60.0  # seconds

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=30.0)
        return self._http

    async def close(self):
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    # -------------------------------------------------------------------
    # Embedding helpers
    # -------------------------------------------------------------------
    async def _embed(self, texts: list[str]) -> np.ndarray:
        """Get embeddings from local qwen3-embed-8b on DEV:8001."""
        client = await self._client()
        resp = await client.post(
            EMBEDDING_URL,
            json={"input": texts, "model": EMBEDDING_MODEL},
        )
        resp.raise_for_status()
        data = resp.json()
        vectors = [item["embedding"] for item in data["data"]]
        return np.array(vectors, dtype=np.float32)

    async def build_index(self):
        """Compute centroid embeddings for each task type. Call once at startup."""
        if EMBEDDINGS_CACHE.exists():
            try:
                loaded = np.load(EMBEDDINGS_CACHE, allow_pickle=True)
                self.index.centroids = {k: loaded[k] for k in loaded.files}
                if self.index.centroids:
                    first = next(iter(self.index.centroids.values()))
                    self.index.dim = first.shape[0]
                    self.index.ready = True
                    log.info(
                        f"Loaded embedding index from cache "
                        f"({len(self.index.centroids)} types, dim={self.index.dim})"
                    )
                    return
            except Exception as e:
                log.warning(f"Failed to load embedding cache, rebuilding: {e}")

        log.info("Building embedding index for task type classification...")
        all_texts: list[str] = []
        type_ranges: list[tuple[str, int, int]] = []
        for task_type, utterances in TASK_TYPE_UTTERANCES.items():
            start = len(all_texts)
            all_texts.extend(utterances)
            type_ranges.append((task_type, start, len(all_texts)))

        try:
            embeddings = await self._embed(all_texts)
        except Exception as e:
            log.error(f"Failed to build embedding index: {e}")
            return

        for task_type, start, end in type_ranges:
            centroid = embeddings[start:end].mean(axis=0)
            # L2 normalize the centroid
            norm = np.linalg.norm(centroid)
            if norm > 0:
                centroid = centroid / norm
            self.index.centroids[task_type] = centroid

        if self.index.centroids:
            first = next(iter(self.index.centroids.values()))
            self.index.dim = first.shape[0]
            self.index.ready = True

        # Cache to disk
        try:
            EMBEDDINGS_CACHE.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(EMBEDDINGS_CACHE, **self.index.centroids)
            log.info(f"Cached embedding index to {EMBEDDINGS_CACHE}")
        except Exception as e:
            log.warning(f"Failed to cache embeddings: {e}")

        log.info(
            f"Embedding index ready: {len(self.index.centroids)} types, "
            f"dim={self.index.dim}"
        )

    # -------------------------------------------------------------------
    # Task classification
    # -------------------------------------------------------------------
    async def classify_task(self, task_description: str) -> tuple[str, float, str]:
        """Classify a task description into a local router task type.

        Returns (task_type, confidence, method) where method is
        'embedding' or 'llm'.
        """
        # --- Attempt 1: embedding similarity ---
        if self.index.ready:
            try:
                t0 = time.monotonic()
                query_vec = (await self._embed([task_description]))[0]
                # Normalize
                norm = np.linalg.norm(query_vec)
                if norm > 0:
                    query_vec = query_vec / norm
                scores = self.index.similarity(query_vec)
                elapsed_ms = (time.monotonic() - t0) * 1000

                if scores and scores[0][1] >= SIMILARITY_THRESHOLD:
                    best_type, best_score = scores[0]
                    log.debug(
                        f"Classified '{task_description[:60]}' -> {best_type} "
                        f"(sim={best_score:.3f}, {elapsed_ms:.0f}ms)"
                    )
                    return best_type, best_score, "embedding"

                log.debug(
                    f"Embedding similarity too low "
                    f"({scores[0][1]:.3f} < {SIMILARITY_THRESHOLD}), "
                    f"falling back to LLM"
                )
            except Exception as e:
                log.warning(
                    f"Embedding classification failed, falling back to LLM: {e}"
                )

        # --- Attempt 2: LLM classification via LiteLLM ---
        return await self._classify_via_llm(task_description)

    async def _classify_via_llm(
        self, task_description: str
    ) -> tuple[str, float, str]:
        """Use local Qwen3.5 via LiteLLM to classify a task."""
        categories = ", ".join(ALL_TASK_TYPES)
        prompt = (
            f"Classify the following task into exactly one category.\n"
            f"Categories: {categories}\n\n"
            f"Task: {task_description}\n\n"
            f"Respond with ONLY the category name, nothing else."
        )
        try:
            t0 = time.monotonic()
            client = await self._client()
            resp = await client.post(
                f"{LITELLM_URL}/v1/chat/completions",
                headers={"Authorization": f"Bearer {LITELLM_KEY}"},
                json={
                    "model": LITELLM_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 20,
                    "temperature": 0.0,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            elapsed_ms = (time.monotonic() - t0) * 1000

            raw = data["choices"][0]["message"]["content"].strip().lower()
            # Strip any thinking tags the model might produce
            if "</think>" in raw:
                raw = raw.split("</think>")[-1].strip()
            # Clean up: just extract the category name
            raw = raw.strip().strip('"').strip("'").strip(".")

            if raw in ALL_TASK_TYPES:
                log.debug(
                    f"LLM classified '{task_description[:60]}' -> {raw} "
                    f"({elapsed_ms:.0f}ms)"
                )
                return raw, 0.8, "llm"

            # Fuzzy match -- find closest
            for tt in ALL_TASK_TYPES:
                if tt in raw or raw in tt:
                    return tt, 0.6, "llm"

            log.warning(
                f"LLM returned unknown category '{raw}', "
                f"defaulting to feature_dev"
            )
            return "feature_dev", 0.3, "llm_fallback"

        except Exception as e:
            log.warning(
                f"LLM classification failed: {e}, defaulting to feature_dev"
            )
            return "feature_dev", 0.2, "error_fallback"

    # -------------------------------------------------------------------
    # CLI availability -- reads from Subscription Burn state
    # -------------------------------------------------------------------
    async def get_available_clis(self) -> dict[str, bool]:
        """Check which CLIs have quota available right now.

        Reads from the Subscription Burn /status endpoint on DEV:8065.
        Returns {cli_name: has_quota}.
        """
        now = time.monotonic()
        if now - self._last_availability_check < self._availability_ttl:
            return self._available_clis

        available: dict[str, bool] = {}
        cli_to_subscription: dict[str, str] = {}
        cli_to_provider: dict[str, str] = {}
        try:
            client = await self._client()
            resp = await client.get(f"{SUBSCRIPTION_BURN_URL}/status")
            resp.raise_for_status()
            status = resp.json()
            policy_providers = dict(_load_policy().get("providers") or {})
            catalog_index = _provider_catalog_index()

            for sub_key, sub_status in dict(status.get("subscriptions", {})).items():
                if not isinstance(sub_status, dict):
                    continue
                provider_id = str(sub_status.get("provider_id") or "").strip()
                if not provider_id:
                    continue

                provider_meta = dict(policy_providers.get(provider_id) or {})
                if str(provider_meta.get("routing_posture") or "") != "ordinary_auto":
                    continue

                catalog_entry = catalog_index.get(provider_id, {})
                if str(catalog_entry.get("access_mode") or "") != "cli":
                    continue

                cli_name = _provider_cli_name(provider_id, catalog_index)
                if not cli_name:
                    continue

                cli_to_subscription[cli_name] = str(sub_key)
                cli_to_provider[cli_name] = provider_id

                # Check if already running
                if sub_status.get("running"):
                    available[cli_name] = False
                    continue

                sub_type = sub_status.get("type")
                if sub_type == "rolling_window":
                    # Available if not currently running
                    available[cli_name] = True
                elif sub_type == "daily_reset":
                    used = sub_status.get("used_today", 0)
                    limit = sub_status.get("daily_limit", 0)
                    available[cli_name] = used < limit if limit else True
                elif sub_type == "monthly_reset":
                    available[cli_name] = True
                elif sub_type == "mixed":
                    available[cli_name] = True  # Perplexity
                elif sub_type == "depleting":
                    remaining = sub_status.get("credits_remaining", 0)
                    available[cli_name] = remaining > 0
                else:
                    available[cli_name] = True

        except Exception as e:
            log.warning(
                f"Failed to check CLI availability from Subscription Burn: {e}"
            )
            available = {cli: True for cli in _known_cli_aliases()}

        self._available_clis = available
        self._cli_to_subscription = cli_to_subscription
        self._cli_to_provider = cli_to_provider
        self._last_availability_check = now
        return available

    # -------------------------------------------------------------------
    # Routing -- the core decision
    # -------------------------------------------------------------------
    async def route(self, task: dict) -> dict[str, Any]:
        """Pick the best CLI for a task.

        Args:
            task: Dict with at least 'description' or 'prompt' key.

        Returns:
            Dict with routing decision including cli, subscription,
            task_type, confidence, method, reason, and alternatives.
        """
        description = task.get("description", task.get("prompt", ""))
        if not description:
            return self._fallback_route("empty_task")

        # 1. Classify the task
        task_type, confidence, method = await self.classify_task(description)

        # 2. Get preferred CLIs for this task type from canonical routing truth.
        preferred_pairs = _canonical_cli_candidates(task_type, description)
        preferred = [cli_name for _, cli_name in preferred_pairs]
        for provider_id, cli_name in preferred_pairs:
            self._cli_to_provider.setdefault(cli_name, provider_id)
        if not preferred:
            fallback_pairs = _canonical_cli_candidates("feature_dev", description)
            preferred = [cli_name for _, cli_name in fallback_pairs] or ["claude"]
            for provider_id, cli_name in fallback_pairs:
                self._cli_to_provider.setdefault(cli_name, provider_id)

        # 3. Check availability
        available = await self.get_available_clis()

        # 4. Apply learned weights if we have enough data
        ranked = self._rank_clis(preferred, task_type, available)

        if not ranked:
            return self._fallback_route(f"no_available_cli_for_{task_type}")

        chosen = ranked[0]
        alternatives = ranked[1:]

        reason_parts = [f"task_type={task_type}"]
        win_rate = self.history.win_rate(chosen, task_type)
        if win_rate is not None:
            reason_parts.append(f"learned_win_rate={win_rate:.2f}")
        else:
            reason_parts.append("policy_preference")
        reason_parts.append(f"classified_by={method}")
        task_class = str(_task_profile(task_type).get("task_class") or "")
        if task_class:
            reason_parts.append(f"policy_task_class={task_class}")

        return {
            "cli": chosen,
            "subscription": self._cli_to_subscription.get(chosen, "unknown"),
            "provider": self._cli_to_provider.get(chosen, "unknown"),
            "task_type": task_type,
            "confidence": round(confidence, 3),
            "method": method,
            "reason": ", ".join(reason_parts),
            "alternatives": alternatives,
        }

    def _rank_clis(
        self,
        preferred: list[str],
        task_type: str,
        available: dict[str, bool],
    ) -> list[str]:
        """Rank CLIs by preference, adjusted by learned win rates.

        Scoring: static_rank_score + learned_bonus.
        - Static rank score: 1.0 for first preferred, 0.8 for second, etc.
        - Learned bonus: (win_rate - 0.5) * 0.4 after MIN_SAMPLES
        - Unavailable CLIs are filtered out.
        """
        candidates: list[tuple[str, float]] = []

        for i, cli in enumerate(preferred):
            if not available.get(cli, False):
                continue

            # Static score from position in preference list
            static_score = max(0, 1.0 - i * 0.2)

            # Learned adjustment
            learned_bonus = 0.0
            win_rate = self.history.win_rate(cli, task_type)
            if win_rate is not None:
                # Shift so 50% is neutral, >50% bonus, <50% penalty
                learned_bonus = (win_rate - 0.5) * 0.4

            candidates.append((cli, static_score + learned_bonus))

        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        return [cli for cli, _ in candidates]

    def _fallback_route(self, reason: str) -> dict[str, Any]:
        fallback_pairs = _canonical_cli_candidates("feature_dev", "Implement the next feature slice")
        chosen_cli = fallback_pairs[0][1] if fallback_pairs else "claude"
        chosen_provider = fallback_pairs[0][0] if fallback_pairs else "unknown"
        return {
            "cli": chosen_cli,
            "subscription": self._cli_to_subscription.get(chosen_cli, "unknown"),
            "provider": chosen_provider,
            "task_type": "feature_dev",
            "confidence": 0.0,
            "method": "fallback",
            "reason": reason,
            "alternatives": [],
        }

    # -------------------------------------------------------------------
    # Result recording
    # -------------------------------------------------------------------
    def record_result(
        self, cli: str, task_type: str, success: bool, duration: float
    ):
        """Record outcome to improve routing over time."""
        self.history.record(cli, task_type, success, duration)
        log.info(
            f"Recorded: {cli} x {task_type} -> "
            f"{'success' if success else 'failure'} ({duration:.1f}s)"
        )

    # -------------------------------------------------------------------
    # Dispatch -- route + launch in one call
    # -------------------------------------------------------------------
    async def dispatch(
        self,
        task: dict,
        dry_run: bool = False,
        operator_action: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Route a task and trigger execution via Subscription Burn.

        Calls the Subscription Burn /burn/{subscription} endpoint after
        routing, so the task gets launched through the normal process
        management path.
        """
        routing = await self.route(task)

        if dry_run:
            return {"routing": routing, "dispatch": "dry_run"}

        sub_key = routing["subscription"]
        try:
            client = await self._client()
            payload = {"operator_action": dict(operator_action)} if operator_action else {}
            resp = await client.post(f"{SUBSCRIPTION_BURN_URL}/burn/{sub_key}", json=payload)
            burn_result = resp.json()
        except Exception as e:
            burn_result = {"error": str(e)}

        return {"routing": routing, "dispatch": burn_result}

    # -------------------------------------------------------------------
    # Stats / introspection
    # -------------------------------------------------------------------
    def stats(self) -> dict[str, Any]:
        """Return routing statistics for API responses."""
        task_rules = {
            task_type: [
                cli_name
                for _, cli_name in _canonical_cli_candidates(
                    task_type,
                    TASK_TYPE_UTTERANCES.get(task_type, [task_type])[0],
                )
            ]
            for task_type in ALL_TASK_TYPES
        }
        return {
            "index_ready": self.index.ready,
            "index_types": len(self.index.centroids),
            "index_dim": self.index.dim,
            "history": self.history.summary(),
            "task_rules": task_rules,
            "cli_map": dict(self._cli_to_subscription),
            "similarity_threshold": SIMILARITY_THRESHOLD,
            "min_samples_for_learning": MIN_SAMPLES_FOR_LEARNING,
        }

    def invalidate_cache(self):
        """Force rebuild of embedding index on next build_index() call."""
        if EMBEDDINGS_CACHE.exists():
            EMBEDDINGS_CACHE.unlink()
            log.info("Embedding cache invalidated")
        self.index = EmbeddingIndex()


# ---------------------------------------------------------------------------
# FastAPI integration -- endpoints to add to Subscription Burn
# ---------------------------------------------------------------------------
def register_router_endpoints(app, router_instance: CLIRouter, *, service_name: str = SERVICE_NAME):
    """Register /route, /dispatch, /router-stats endpoints on the FastAPI app.

    Called from Subscription Burn after creating the CLIRouter instance.

    Usage in Subscription Burn::

        from cli_router import CLIRouter, register_router_endpoints

        router = CLIRouter()

        @asynccontextmanager
        async def lifespan(app):
            await router.build_index()
            yield
            await router.close()

        register_router_endpoints(app, router)
    """
    from fastapi import HTTPException as _HTTPException
    from pydantic import BaseModel as _BaseModel

    class RouteRequest(_BaseModel):
        description: str
        prompt: str | None = None
        working_dir: str | None = None

    class DispatchRequest(_BaseModel):
        description: str
        prompt: str | None = None
        working_dir: str | None = None
        dry_run: bool = False

    class RecordRequest(_BaseModel):
        cli: str
        task_type: str
        success: bool
        duration: float

    @app.post("/route")
    async def route_task(req: RouteRequest):
        """Classify a task and return the recommended CLI."""
        task = {"description": req.description}
        if req.prompt:
            task["prompt"] = req.prompt
        if req.working_dir:
            task["working_dir"] = req.working_dir
        return await router_instance.route(task)

    @app.post("/dispatch")
    async def dispatch_task(req: DispatchRequest, request: Request):
        """Route a task to the best CLI and launch it."""
        _body, action, denial = await _load_operator_body(
            request,
            route="/dispatch",
            action_class="admin",
            default_reason="Dispatched a routed subscription burn task",
        )
        if denial:
            return denial
        task = {"description": req.description}
        if req.prompt:
            task["prompt"] = req.prompt
        if req.working_dir:
            task["working_dir"] = req.working_dir
        result = await router_instance.dispatch(
            task,
            dry_run=req.dry_run,
            operator_action=action.to_dict(),
        )
        dispatch_payload = result.get("dispatch")
        if isinstance(dispatch_payload, dict) and dispatch_payload.get("error") and not dispatch_payload.get("skipped"):
            await emit_operator_audit_event(
                service=service_name,
                route="/dispatch",
                action_class="admin",
                decision="denied",
                status_code=500,
                action=action,
                detail=str(dispatch_payload.get("error")),
                target=str(result["routing"]["subscription"]),
                metadata={
                    "cli": str(result["routing"]["cli"]),
                    "task_type": str(result["routing"]["task_type"]),
                    "dry_run": req.dry_run,
                },
            )
            return JSONResponse(status_code=500, content=result)
        await emit_operator_audit_event(
            service=service_name,
            route="/dispatch",
            action_class="admin",
            decision="accepted",
            status_code=200,
            action=action,
            detail=f"Routed task as {result['routing']['subscription']}",
            target=str(result["routing"]["subscription"]),
            metadata={
                "cli": str(result["routing"]["cli"]),
                "task_type": str(result["routing"]["task_type"]),
                "dry_run": req.dry_run,
            },
        )
        return result

    @app.post("/record-result")
    async def record_result(req: RecordRequest, request: Request):
        """Record task outcome for the learning loop."""
        _body, action, denial = await _load_operator_body(
            request,
            route="/record-result",
            action_class="operator",
            default_reason=f"Recorded CLI routing outcome for {req.cli}",
        )
        if denial:
            return denial
        known_clis = set(_known_cli_aliases()) | set(router_instance._cli_to_subscription)
        known_subscriptions = set(router_instance._cli_to_subscription.values())
        if req.cli not in known_clis and req.cli not in known_subscriptions:
            await emit_operator_audit_event(
                service=service_name,
                route="/record-result",
                action_class="operator",
                decision="denied",
                status_code=400,
                action=action,
                detail=f"Unknown CLI: {req.cli}",
                target=req.cli,
            )
            raise _HTTPException(status_code=400, detail=f"Unknown CLI: {req.cli}")
        if req.task_type not in ALL_TASK_TYPES:
            await emit_operator_audit_event(
                service=service_name,
                route="/record-result",
                action_class="operator",
                decision="denied",
                status_code=400,
                action=action,
                detail=f"Unknown task type: {req.task_type}",
                target=req.task_type,
            )
            raise _HTTPException(status_code=400, detail=f"Unknown task type: {req.task_type}")
        router_instance.record_result(
            req.cli, req.task_type, req.success, req.duration
        )
        await emit_operator_audit_event(
            service=service_name,
            route="/record-result",
            action_class="operator",
            decision="accepted",
            status_code=200,
            action=action,
            detail=f"Recorded routing result for {req.cli}",
            target=req.cli,
            metadata={
                "task_type": req.task_type,
                "success": req.success,
                "duration": req.duration,
            },
        )
        return {"recorded": True}

    @app.get("/router-stats")
    async def router_stats():
        """Return routing statistics and learned performance data."""
        available = await router_instance.get_available_clis()
        stats = router_instance.stats()
        stats["available_clis"] = available
        return stats

    @app.post("/classify")
    async def classify_task_endpoint(req: RouteRequest):
        """Classify a task description without routing."""
        task_type, confidence, method = await router_instance.classify_task(
            req.description
        )
        return {
            "task_type": task_type,
            "confidence": round(confidence, 3),
            "method": method,
            "preferred_clis": [
                cli_name for _, cli_name in _canonical_cli_candidates(task_type, req.description)
            ],
        }

    @app.post("/router/invalidate-cache")
    async def invalidate_cache(request: Request):
        """Force rebuild of embedding index."""
        _body, action, denial = await _load_operator_body(
            request,
            route="/router/invalidate-cache",
            action_class="admin",
            default_reason="Rebuilt the CLI router embedding cache",
        )
        if denial:
            return denial
        router_instance.invalidate_cache()
        await router_instance.build_index()
        await emit_operator_audit_event(
            service=service_name,
            route="/router/invalidate-cache",
            action_class="admin",
            decision="accepted",
            status_code=200,
            action=action,
            detail="Rebuilt the CLI router embedding cache",
            metadata={"types": len(router_instance.index.centroids)},
        )
        return {
            "status": "rebuilt",
            "types": len(router_instance.index.centroids),
        }

    log.info(
        "CLI Router endpoints registered: "
        "/route, /dispatch, /classify, /router-stats, /record-result"
    )


# ---------------------------------------------------------------------------
# Standalone test -- run directly to verify classification
# ---------------------------------------------------------------------------
async def _self_test():
    """Quick self-test: classify sample tasks, print results."""
    logging.basicConfig(level=logging.DEBUG)
    router = CLIRouter()
    await router.build_index()

    test_tasks = [
        "Audit all FastAPI services for consistent error handling patterns",
        "Fix the failing unit test in the memory service",
        "Write unit tests for the CLI router module",
        "Research alternatives to Redis for the working memory tier",
        "Refactor MCP server shared utilities into a common module",
        "Generate documentation for the subscription burn API",
        "Design the architecture for a distributed task queue",
        "Deep research on GPU scheduling algorithms with citations",
        "Debug the memory leak in the perception service",
        "Review the pull request for the new gateway middleware",
    ]

    print("\n=== CLI Router Self-Test ===\n")
    for desc in test_tasks:
        result = await router.route({"description": desc})
        print(
            f"  {desc[:65]:<65}  ->  {result['task_type']:<15} "
            f"-> {result['cli']:<10} "
            f"({result['method']}, conf={result['confidence']:.2f})"
        )

    print(
        f"\nIndex: {len(router.index.centroids)} types, "
        f"dim={router.index.dim}"
    )
    await router.close()


if __name__ == "__main__":
    asyncio.run(_self_test())
