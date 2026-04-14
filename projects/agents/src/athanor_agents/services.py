from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cached_property
from typing import Mapping

from .config import Settings, settings


def normalize_url(url: str) -> str:
    return url.rstrip("/")


def join_url(base: str, path: str) -> str:
    normalized_base = normalize_url(base)
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"{normalized_base}{normalized_path}"


def ensure_openai_base_url(base: str) -> str:
    normalized = normalize_url(base)
    return normalized if normalized.endswith("/v1") else f"{normalized}/v1"


def ensure_api_root(base: str) -> str:
    normalized = normalize_url(base)
    return normalized if normalized.endswith("/api") else f"{normalized}/api"


def prometheus_host_regex(*hosts: str) -> str:
    return "|".join(re.escape(host).replace(r"\.", "[.]") for host in hosts if host)


@dataclass(frozen=True)
class ServiceEndpoint:
    id: str
    name: str
    node: str
    base_url: str
    description: str = ""
    health_path: str | None = None
    models_path: str | None = None
    headers: Mapping[str, str] = field(default_factory=dict)

    def url(self, path: str = "") -> str:
        return join_url(self.base_url, path) if path else normalize_url(self.base_url)

    @property
    def health_url(self) -> str | None:
        return self.url(self.health_path) if self.health_path else None

    @property
    def models_url(self) -> str | None:
        return self.url(self.models_path) if self.models_path else None


class ServiceRegistry:
    def __init__(self, config: Settings):
        self.config = config

    @cached_property
    def litellm_headers(self) -> dict[str, str]:
        if not self.config.litellm_api_key:
            return {}
        return {"Authorization": f"Bearer {self.config.litellm_api_key}"}

    @cached_property
    def home_assistant_headers(self) -> dict[str, str]:
        if not self.config.ha_token:
            return {"Content-Type": "application/json"}
        return {
            "Authorization": f"Bearer {self.config.ha_token}",
            "Content-Type": "application/json",
        }

    @cached_property
    def neo4j_auth(self) -> tuple[str, str] | None:
        if not self.config.neo4j_password:
            return None
        return (self.config.neo4j_user, self.config.neo4j_password)

    @cached_property
    def litellm_openai_url(self) -> str:
        return ensure_openai_base_url(self.config.litellm_url)

    @cached_property
    def coordinator_openai_url(self) -> str:
        return ensure_openai_base_url(self.config.coordinator_url)

    @cached_property
    def coder_openai_url(self) -> str:
        return ensure_openai_base_url(self.config.coder_url)

    @cached_property
    def worker_openai_url(self) -> str:
        return ensure_openai_base_url(self.config.worker_url)

    @cached_property
    def embedding_openai_url(self) -> str:
        return ensure_openai_base_url(self.config.embedding_url)

    @cached_property
    def reranker_openai_url(self) -> str:
        return ensure_openai_base_url(self.config.reranker_url)

    @cached_property
    def home_assistant_api_url(self) -> str:
        return ensure_api_root(self.config.home_assistant_url)

    @cached_property
    def neo4j_commit_url(self) -> str:
        return join_url(self.config.neo4j_url, "/db/neo4j/tx/commit")

    @cached_property
    def sonarr_api_url(self) -> str:
        return join_url(self.config.sonarr_url, "/api/v3")

    @cached_property
    def radarr_api_url(self) -> str:
        return join_url(self.config.radarr_url, "/api/v3")

    @cached_property
    def prowlarr_api_url(self) -> str:
        return join_url(self.config.prowlarr_url, "/api/v1")

    @cached_property
    def sabnzbd_api_url(self) -> str:
        return join_url(self.config.sabnzbd_url, "/api")

    @cached_property
    def tautulli_api_url(self) -> str:
        return join_url(self.config.tautulli_url, "/api/v2")

    @cached_property
    def stash_graphql_url(self) -> str:
        return join_url(self.config.stash_url, "/graphql")

    @cached_property
    def litellm(self) -> ServiceEndpoint:
        return ServiceEndpoint(
            id="litellm-proxy",
            name="LiteLLM Proxy",
            node="VAULT",
            base_url=self.config.litellm_url,
            description="Canonical routing and alias edge.",
            health_path="/health/readiness",
            models_path="/v1/models",
            headers=self.litellm_headers,
        )

    @cached_property
    def coordinator(self) -> ServiceEndpoint:
        return ServiceEndpoint(
            id="foundry-coordinator",
            name="Foundry Coordinator",
            node="Foundry",
            base_url=self.config.coordinator_url,
            description="Primary reasoning runtime.",
            health_path="/health",
            models_path="/v1/models",
        )

    @cached_property
    def coder(self) -> ServiceEndpoint:
        return ServiceEndpoint(
            id="foundry-coder",
            name="Foundry Coder",
            node="Foundry",
            base_url=self.config.coder_url,
            description="Dedicated autonomous coding runtime.",
            health_path="/health",
            models_path="/v1/models",
        )

    @cached_property
    def worker(self) -> ServiceEndpoint:
        return ServiceEndpoint(
            id="workshop-worker",
            name="Workshop Worker",
            node="Workshop",
            base_url=self.config.worker_url,
            description="Interactive worker runtime.",
            health_path="/health",
            models_path="/v1/models",
        )

    @cached_property
    def embedding(self) -> ServiceEndpoint:
        return ServiceEndpoint(
            id="dev-embedding",
            name="DEV Embedding",
            node="DEV",
            base_url=self.config.embedding_url,
            description="Embedding runtime for retrieval.",
            health_path="/health",
            models_path="/v1/models",
        )

    @cached_property
    def reranker(self) -> ServiceEndpoint:
        return ServiceEndpoint(
            id="dev-reranker",
            name="DEV Reranker",
            node="DEV",
            base_url=self.config.reranker_url,
            description="Reranker runtime for retrieval precision.",
            health_path="/health",
        )

    @cached_property
    def agent_server(self) -> ServiceEndpoint:
        return ServiceEndpoint(
            id="agent-server",
            name="Agent Server",
            node="Foundry",
            base_url=self.config.agent_server_url,
            description="Athanor workforce API.",
            health_path="/health",
        )

    @cached_property
    def qdrant(self) -> ServiceEndpoint:
        return ServiceEndpoint(
            id="qdrant",
            name="Qdrant",
            node="VAULT",
            base_url=self.config.qdrant_url,
            description="Vector store.",
            health_path="/collections",
        )

    @cached_property
    def graphrag(self) -> ServiceEndpoint:
        return ServiceEndpoint(
            id="graphrag",
            name="GraphRAG",
            node="Foundry",
            base_url=self.config.graphrag_url,
            description="Governed GraphRAG retrieval service.",
            health_path="/health",
        )

    @cached_property
    def comfyui(self) -> ServiceEndpoint:
        return ServiceEndpoint(
            id="comfyui",
            name="ComfyUI",
            node="Workshop",
            base_url=self.config.comfyui_url,
            description="Creative workflow runtime.",
            health_path="/system_stats",
        )

    @cached_property
    def dashboard(self) -> ServiceEndpoint:
        return ServiceEndpoint(
            id="dashboard",
            name="Dashboard",
            node="DEV",
            base_url=self.config.dashboard_url,
            description="Command Center UI.",
        )

    @cached_property
    def prometheus(self) -> ServiceEndpoint:
        return ServiceEndpoint(
            id="prometheus",
            name="Prometheus",
            node="VAULT",
            base_url=self.config.prometheus_url,
            description="Metrics collection.",
            health_path="/-/healthy",
        )

    @cached_property
    def grafana(self) -> ServiceEndpoint:
        return ServiceEndpoint(
            id="grafana",
            name="Grafana",
            node="VAULT",
            base_url=self.config.grafana_url,
            description="Dashboards and alerting.",
            health_path="/api/health",
        )

    @cached_property
    def sonarr(self) -> ServiceEndpoint:
        return ServiceEndpoint(
            id="sonarr",
            name="Sonarr",
            node="VAULT",
            base_url=self.config.sonarr_url,
            description="TV acquisition.",
            health_path="/ping",
        )

    @cached_property
    def radarr(self) -> ServiceEndpoint:
        return ServiceEndpoint(
            id="radarr",
            name="Radarr",
            node="VAULT",
            base_url=self.config.radarr_url,
            description="Movie acquisition.",
            health_path="/ping",
        )

    @cached_property
    def sabnzbd(self) -> ServiceEndpoint:
        return ServiceEndpoint(
            id="sabnzbd",
            name="SABnzbd",
            node="VAULT",
            base_url=self.config.sabnzbd_url,
            description="Downloader.",
            health_path="/api?mode=version&output=json",
        )

    @cached_property
    def prowlarr(self) -> ServiceEndpoint:
        headers = {"X-Api-Key": self.config.prowlarr_api_key} if self.config.prowlarr_api_key else {}
        return ServiceEndpoint(
            id="prowlarr",
            name="Prowlarr",
            node="VAULT",
            base_url=self.config.prowlarr_url,
            description="Indexer manager.",
            health_path="/api/v1/health",
            headers=headers,
        )

    @cached_property
    def tautulli(self) -> ServiceEndpoint:
        return ServiceEndpoint(
            id="tautulli",
            name="Tautulli",
            node="VAULT",
            base_url=self.config.tautulli_url,
            description="Plex analytics.",
        )

    @cached_property
    def stash(self) -> ServiceEndpoint:
        return ServiceEndpoint(
            id="stash",
            name="Stash",
            node="VAULT",
            base_url=self.config.stash_url,
            description="Catalog runtime.",
        )

    @cached_property
    def plex(self) -> ServiceEndpoint:
        return ServiceEndpoint(
            id="plex",
            name="Plex",
            node="VAULT",
            base_url=self.config.plex_url,
            description="Media server.",
            health_path="/identity",
        )

    @cached_property
    def home_assistant(self) -> ServiceEndpoint:
        return ServiceEndpoint(
            id="home-assistant",
            name="Home Assistant",
            node="VAULT",
            base_url=self.config.home_assistant_url,
            description="Home control plane.",
            health_path="/api/",
            headers=self.home_assistant_headers,
        )

    @cached_property
    def neo4j(self) -> ServiceEndpoint:
        return ServiceEndpoint(
            id="neo4j",
            name="Neo4j",
            node="VAULT",
            base_url=self.config.neo4j_url,
            description="Graph memory.",
        )

    @cached_property
    def open_webui(self) -> ServiceEndpoint:
        return ServiceEndpoint(
            id="open-webui",
            name="Open WebUI",
            node="Workshop",
            base_url=self.config.open_webui_url,
            description="Direct raw chat surface.",
        )

    @cached_property
    def vault_open_webui(self) -> ServiceEndpoint:
        return ServiceEndpoint(
            id="vault-open-webui",
            name="VAULT Open WebUI",
            node="VAULT",
            base_url=self.config.vault_open_webui_url,
            description="LiteLLM-routed chat surface.",
        )

    @cached_property
    def gpu_orchestrator(self) -> ServiceEndpoint:
        return ServiceEndpoint(
            id="gpu-orchestrator",
            name="GPU Orchestrator",
            node="Foundry",
            base_url=self.config.gpu_orchestrator_url,
            description="GPU orchestration control plane.",
            health_path="/health",
        )

    @cached_property
    def langfuse(self) -> ServiceEndpoint:
        return ServiceEndpoint(
            id="langfuse",
            name="LangFuse",
            node="VAULT",
            base_url=self.config.langfuse_url,
            description="Tracing and evaluation.",
        )

    @cached_property
    def eoq(self) -> ServiceEndpoint:
        return ServiceEndpoint(
            id="eoq",
            name="Empire of Broken Queens",
            node="Workshop",
            base_url=self.config.eoq_url,
            description="First-class tenant app.",
        )

    @cached_property
    def service_checks(self) -> list[ServiceEndpoint]:
        return [
            self.litellm,
            self.coder,
            self.embedding,
            self.reranker,
            self.agent_server,
            self.graphrag,
            self.qdrant,
            self.comfyui,
            self.dashboard,
            self.prometheus,
            self.grafana,
            self.sonarr,
            self.radarr,
            self.prowlarr,
            self.sabnzbd,
            self.tautulli,
            self.stash,
            self.plex,
            self.home_assistant,
            self.neo4j,
            self.open_webui,
            self.vault_open_webui,
            self.gpu_orchestrator,
            self.langfuse,
            self.eoq,
        ]

    @cached_property
    def model_targets(self) -> list[tuple[str, ServiceEndpoint]]:
        return [
            ("LiteLLM proxy", self.litellm),
            ("Foundry coder", self.coder),
            ("DEV embedding", self.embedding),
        ]

    @cached_property
    def inference_health_checks(self) -> dict[str, ServiceEndpoint]:
        return {
            "coder": self.coder,
            "litellm": self.litellm,
            "embedding": self.embedding,
            "reranker": self.reranker,
        }

    @cached_property
    def inference_instance_regex(self) -> str:
        return prometheus_host_regex(self.config.node1_host, self.config.node2_host)

    @cached_property
    def vault_instance_regex(self) -> str:
        return prometheus_host_regex(self.config.vault_host)


registry = ServiceRegistry(settings)
