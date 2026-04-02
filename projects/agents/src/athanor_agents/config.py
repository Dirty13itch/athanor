from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_url(url: str) -> str:
    return url.rstrip("/")


def _ensure_openai_base_url(url: str) -> str:
    normalized = _normalize_url(url)
    return normalized if normalized.endswith("/v1") else f"{normalized}/v1"


@lru_cache(maxsize=1)
def _platform_topology() -> dict[str, Any]:
    try:
        from .model_governance import get_platform_topology

        topology = get_platform_topology()
        if isinstance(topology, dict):
            return topology
    except Exception:
        pass
    return {"nodes": [], "services": []}


@lru_cache(maxsize=1)
def _node_definitions() -> dict[str, dict[str, Any]]:
    return {
        str(node.get("id")): dict(node)
        for node in _platform_topology().get("nodes", [])
        if isinstance(node, dict) and node.get("id")
    }


@lru_cache(maxsize=1)
def _service_definitions() -> dict[str, dict[str, Any]]:
    return {
        str(service.get("id")): dict(service)
        for service in _platform_topology().get("services", [])
        if isinstance(service, dict) and service.get("id")
    }


def _node_default(node_id: str, fallback: str) -> str:
    node = _node_definitions().get(node_id, {})
    value = str(node.get("default_host") or "").strip()
    return value or fallback


def _service_default_url(service_id: str, fallback: str) -> str:
    service = _service_definitions().get(service_id)
    if not service:
        return fallback

    node_id = str(service.get("node") or "").strip()
    node_host = _node_default(node_id, "")
    scheme = str(service.get("scheme") or "").strip()
    try:
        port = int(service.get("port") or 0)
    except (TypeError, ValueError):
        return fallback
    path = str(service.get("path") or "")
    if not node_host or not scheme or port <= 0:
        return fallback
    return f"{scheme}://{node_host}:{port}{path}"


def _default_agent_descriptor_path() -> str:
    target_parts = ("config", "automation-backbone", "agent-descriptor-registry.json")
    for base in Path(__file__).resolve().parents:
        candidate = base.joinpath(*target_parts)
        if candidate.exists():
            return str(candidate)
    return "/workspace/config/automation-backbone/agent-descriptor-registry.json"


def _default_domain_packet_path() -> str:
    target_parts = ("config", "automation-backbone", "domain-packets-registry.json")
    for base in Path(__file__).resolve().parents:
        candidate = base.joinpath(*target_parts)
        if candidate.exists():
            return str(candidate)
    return "/workspace/config/automation-backbone/domain-packets-registry.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    runtime_environment: str = Field(
        default="production",
        validation_alias=AliasChoices("ATHANOR_ENV", "ATHANOR_RUNTIME_ENV", "APP_ENV", "ENVIRONMENT"),
    )

    node1_host: str = Field(
        default_factory=lambda: _node_default("foundry", "192.168.1.244"),
        validation_alias=AliasChoices("ATHANOR_NODE1_HOST"),
    )
    node2_host: str = Field(
        default_factory=lambda: _node_default("workshop", "192.168.1.225"),
        validation_alias=AliasChoices("ATHANOR_NODE2_HOST"),
    )
    vault_host: str = Field(
        default_factory=lambda: _node_default("vault", "192.168.1.203"),
        validation_alias=AliasChoices("ATHANOR_VAULT_HOST"),
    )
    dev_host: str = Field(
        default_factory=lambda: _node_default("dev", "192.168.1.189"),
        validation_alias=AliasChoices("ATHANOR_DEV_HOST"),
    )

    litellm_url: str = Field(
        default_factory=lambda: _service_default_url("litellm", "http://192.168.1.203:4000"),
        validation_alias=AliasChoices("ATHANOR_LITELLM_URL", "ATHANOR_LLM_BASE_URL"),
    )
    litellm_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("ATHANOR_LITELLM_API_KEY", "ATHANOR_LLM_API_KEY"),
    )
    llm_model: str = Field(
        default="reasoning",
        validation_alias=AliasChoices("ATHANOR_LLM_MODEL"),
    )
    llm_model_fast: str = Field(
        default="fast",
        validation_alias=AliasChoices("ATHANOR_LLM_MODEL_FAST"),
    )

    router_reactive_model: str = Field(
        default="fast",
        validation_alias=AliasChoices("ATHANOR_ROUTER_REACTIVE_MODEL"),
    )
    router_reactive_max_tokens: int = Field(
        default=256,
        validation_alias=AliasChoices("ATHANOR_ROUTER_REACTIVE_MAX_TOKENS"),
    )
    router_reactive_temperature: float = Field(
        default=0.3,
        validation_alias=AliasChoices("ATHANOR_ROUTER_REACTIVE_TEMPERATURE"),
    )
    router_tactical_model: str = Field(
        default="worker",
        validation_alias=AliasChoices("ATHANOR_ROUTER_TACTICAL_MODEL"),
    )
    router_tactical_max_tokens: int = Field(
        default=1024,
        validation_alias=AliasChoices("ATHANOR_ROUTER_TACTICAL_MAX_TOKENS"),
    )
    router_deliberative_model: str = Field(
        default="reasoning",
        validation_alias=AliasChoices("ATHANOR_ROUTER_DELIBERATIVE_MODEL"),
    )
    router_deliberative_max_tokens: int = Field(
        default=4096,
        validation_alias=AliasChoices("ATHANOR_ROUTER_DELIBERATIVE_MAX_TOKENS"),
    )

    coordinator_url: str = Field(
        default_factory=lambda: _service_default_url("vllm_coordinator", "http://192.168.1.244:8000"),
        validation_alias=AliasChoices(
            "ATHANOR_VLLM_COORDINATOR_URL",
            "ATHANOR_VLLM_NODE1_URL",
        ),
    )
    coder_url: str = Field(
        default_factory=lambda: _service_default_url("vllm_coder", "http://192.168.1.244:8006"),
        validation_alias=AliasChoices("ATHANOR_VLLM_CODER_URL", "ATHANOR_VLLM_UTILITY_URL"),
    )
    worker_url: str = Field(
        default_factory=lambda: _service_default_url("vllm_worker", "http://192.168.1.225:8010"),
        validation_alias=AliasChoices(
            "ATHANOR_VLLM_WORKER_URL",
            "ATHANOR_VLLM_NODE2_URL",
        ),
    )
    embedding_url: str = Field(
        default_factory=lambda: _service_default_url("embedding", "http://192.168.1.189:8001"),
        validation_alias=AliasChoices("ATHANOR_VLLM_EMBEDDING_URL"),
    )
    reranker_url: str = Field(
        default_factory=lambda: _service_default_url("reranker", "http://192.168.1.189:8003"),
        validation_alias=AliasChoices("ATHANOR_VLLM_RERANKER_URL"),
    )
    vision_url: str = Field(
        default_factory=lambda: _service_default_url("vllm_vision", "http://192.168.1.225:8010"),
        validation_alias=AliasChoices("ATHANOR_VLLM_VISION_URL"),
    )

    agent_server_url: str = Field(
        default_factory=lambda: _service_default_url("agent_server", "http://192.168.1.244:9000"),
        validation_alias=AliasChoices("ATHANOR_AGENT_SERVER_URL"),
    )
    dashboard_url: str = Field(
        default_factory=lambda: _service_default_url("dashboard", "http://dev.athanor.local:3001"),
        validation_alias=AliasChoices("ATHANOR_DASHBOARD_URL"),
    )
    prometheus_url: str = Field(
        default_factory=lambda: _service_default_url("prometheus", "http://192.168.1.203:9090"),
        validation_alias=AliasChoices("ATHANOR_PROMETHEUS_URL"),
    )
    grafana_url: str = Field(
        default_factory=lambda: _service_default_url("grafana", "http://192.168.1.203:3000"),
        validation_alias=AliasChoices("ATHANOR_GRAFANA_URL"),
    )
    qdrant_url: str = Field(
        default_factory=lambda: _service_default_url("qdrant", "http://192.168.1.203:6333"),
        validation_alias=AliasChoices("ATHANOR_QDRANT_URL"),
    )
    redis_url: str = Field(
        default_factory=lambda: _service_default_url("redis", "redis://192.168.1.203:6379/0"),
        validation_alias=AliasChoices("ATHANOR_REDIS_URL"),
    )
    redis_password: str = Field(
        default="",
        validation_alias=AliasChoices("ATHANOR_REDIS_PASSWORD"),
    )
    postgres_url: str = Field(
        default="",
        validation_alias=AliasChoices("ATHANOR_POSTGRES_URL"),
    )
    subscription_policy_path: str = Field(
        default="",
        validation_alias=AliasChoices("ATHANOR_SUBSCRIPTION_POLICY_PATH"),
    )
    agent_descriptor_path: str = Field(
        default=_default_agent_descriptor_path(),
        validation_alias=AliasChoices("ATHANOR_AGENT_DESCRIPTOR_PATH"),
    )
    domain_packet_path: str = Field(
        default=_default_domain_packet_path(),
        validation_alias=AliasChoices("ATHANOR_DOMAIN_PACKET_PATH"),
    )
    neo4j_url: str = Field(
        default_factory=lambda: _service_default_url("neo4j_http", "http://192.168.1.203:7474"),
        validation_alias=AliasChoices("ATHANOR_NEO4J_URL"),
    )
    neo4j_user: str = Field(
        default="neo4j",
        validation_alias=AliasChoices("ATHANOR_NEO4J_USER"),
    )
    neo4j_password: str = Field(
        default="",
        validation_alias=AliasChoices("ATHANOR_NEO4J_PASSWORD"),
    )

    home_assistant_url: str = Field(
        default="http://192.168.1.203:8123",
        validation_alias=AliasChoices("ATHANOR_HOME_ASSISTANT_URL"),
    )
    ha_token: str = Field(
        default="",
        validation_alias=AliasChoices("ATHANOR_HA_TOKEN"),
    )

    sonarr_url: str = Field(
        default="http://192.168.1.203:8989",
        validation_alias=AliasChoices("ATHANOR_SONARR_URL"),
    )
    sonarr_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("ATHANOR_SONARR_API_KEY"),
    )
    radarr_url: str = Field(
        default="http://192.168.1.203:7878",
        validation_alias=AliasChoices("ATHANOR_RADARR_URL"),
    )
    radarr_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("ATHANOR_RADARR_API_KEY"),
    )
    tautulli_url: str = Field(
        default="http://192.168.1.203:8181",
        validation_alias=AliasChoices("ATHANOR_TAUTULLI_URL"),
    )
    tautulli_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("ATHANOR_TAUTULLI_API_KEY"),
    )
    plex_url: str = Field(
        default="http://192.168.1.203:32400",
        validation_alias=AliasChoices("ATHANOR_PLEX_URL"),
    )
    prowlarr_url: str = Field(
        default="http://192.168.1.203:9696",
        validation_alias=AliasChoices("ATHANOR_PROWLARR_URL"),
    )
    prowlarr_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("ATHANOR_PROWLARR_API_KEY"),
    )
    sabnzbd_url: str = Field(
        default="http://192.168.1.203:8080",
        validation_alias=AliasChoices("ATHANOR_SABNZBD_URL"),
    )
    sabnzbd_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("ATHANOR_SABNZBD_API_KEY"),
    )
    stash_url: str = Field(
        default_factory=lambda: _service_default_url("stash", "http://192.168.1.203:9999"),
        validation_alias=AliasChoices("ATHANOR_STASH_URL"),
    )

    comfyui_url: str = Field(
        default_factory=lambda: _service_default_url("comfyui", "http://192.168.1.225:8188"),
        validation_alias=AliasChoices("ATHANOR_COMFYUI_URL"),
    )
    open_webui_url: str = Field(
        default="http://192.168.1.225:3000",
        validation_alias=AliasChoices("ATHANOR_OPEN_WEBUI_URL"),
    )
    vault_open_webui_url: str = Field(
        default="http://192.168.1.203:3090",
        validation_alias=AliasChoices("ATHANOR_VAULT_OPEN_WEBUI_URL"),
    )
    eoq_url: str = Field(
        default="http://192.168.1.225:3002",
        validation_alias=AliasChoices("ATHANOR_EOQ_URL", "ATHANOR_EOBQ_URL"),
    )
    speaches_url: str = Field(
        default_factory=lambda: _service_default_url("speaches", "http://192.168.1.244:8200"),
        validation_alias=AliasChoices("ATHANOR_SPEACHES_URL"),
    )
    gpu_orchestrator_url: str = Field(
        default_factory=lambda: _service_default_url("gpu_orchestrator", "http://192.168.1.244:9200"),
        validation_alias=AliasChoices("ATHANOR_GPU_ORCHESTRATOR_URL"),
    )
    provider_bridge_url: str = Field(
        default="",
        validation_alias=AliasChoices("ATHANOR_PROVIDER_BRIDGE_URL"),
    )
    provider_bridge_token: str = Field(
        default="",
        validation_alias=AliasChoices("ATHANOR_PROVIDER_BRIDGE_TOKEN"),
    )
    provider_bridge_timeout_seconds: int = Field(
        default=120,
        validation_alias=AliasChoices("ATHANOR_PROVIDER_BRIDGE_TIMEOUT_SECONDS"),
    )
    langfuse_url: str = Field(
        default_factory=lambda: _service_default_url("langfuse", "http://192.168.1.203:3030"),
        validation_alias=AliasChoices("ATHANOR_LANGFUSE_URL"),
    )

    miniflux_url: str = Field(
        default_factory=lambda: _service_default_url("miniflux", "http://192.168.1.203:8070"),
        validation_alias=AliasChoices("ATHANOR_MINIFLUX_URL", "MINIFLUX_URL"),
    )
    miniflux_user: str = Field(
        default="admin",
        validation_alias=AliasChoices("ATHANOR_MINIFLUX_USER", "MINIFLUX_USER"),
    )
    miniflux_pass: str = Field(
        default="",
        validation_alias=AliasChoices("ATHANOR_MINIFLUX_PASS", "MINIFLUX_PASS"),
    )

    ntfy_url: str = Field(
        default_factory=lambda: _service_default_url("ntfy", "http://192.168.1.203:8880"),
        validation_alias=AliasChoices("ATHANOR_NTFY_URL"),
    )
    ntfy_topic: str = Field(
        default="athanor",
        validation_alias=AliasChoices("ATHANOR_NTFY_TOPIC"),
    )

    api_bearer_token: str = Field(
        default="",
        validation_alias=AliasChoices("ATHANOR_AGENT_API_TOKEN", "ATHANOR_API_BEARER_TOKEN"),
    )

    host: str = Field(default="0.0.0.0", validation_alias=AliasChoices("ATHANOR_HOST"))
    port: int = Field(default=9000, validation_alias=AliasChoices("ATHANOR_PORT"))

    @property
    def llm_base_url(self) -> str:
        return _ensure_openai_base_url(self.litellm_url)

    @property
    def llm_api_key(self) -> str:
        return self.litellm_api_key

    @property
    def vllm_node1_url(self) -> str:
        return _ensure_openai_base_url(self.coordinator_url)

    @property
    def vllm_node2_url(self) -> str:
        return _ensure_openai_base_url(self.worker_url)

    @property
    def vllm_embedding_url(self) -> str:
        return _ensure_openai_base_url(self.embedding_url)

    @property
    def vllm_reranker_url(self) -> str:
        return _ensure_openai_base_url(self.reranker_url)


settings = Settings()
