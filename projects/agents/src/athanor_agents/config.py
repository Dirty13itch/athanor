from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_url(url: str) -> str:
    return url.rstrip("/")


def _ensure_openai_base_url(url: str) -> str:
    normalized = _normalize_url(url)
    return normalized if normalized.endswith("/v1") else f"{normalized}/v1"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    node1_host: str = Field(
        default="192.168.1.244",
        validation_alias=AliasChoices("ATHANOR_NODE1_HOST"),
    )
    node2_host: str = Field(
        default="192.168.1.225",
        validation_alias=AliasChoices("ATHANOR_NODE2_HOST"),
    )
    vault_host: str = Field(
        default="192.168.1.203",
        validation_alias=AliasChoices("ATHANOR_VAULT_HOST"),
    )
    dev_host: str = Field(
        default="192.168.1.189",
        validation_alias=AliasChoices("ATHANOR_DEV_HOST"),
    )

    litellm_url: str = Field(
        default="http://192.168.1.203:4000",
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
        default="http://192.168.1.244:8000",
        validation_alias=AliasChoices(
            "ATHANOR_VLLM_COORDINATOR_URL",
            "ATHANOR_VLLM_NODE1_URL",
        ),
    )
    coder_url: str = Field(
        default="http://192.168.1.244:8006",
        validation_alias=AliasChoices("ATHANOR_VLLM_CODER_URL", "ATHANOR_VLLM_UTILITY_URL"),
    )
    worker_url: str = Field(
        default="http://192.168.1.225:8000",
        validation_alias=AliasChoices(
            "ATHANOR_VLLM_WORKER_URL",
            "ATHANOR_VLLM_NODE2_URL",
        ),
    )
    embedding_url: str = Field(
        default="http://192.168.1.189:8001",
        validation_alias=AliasChoices("ATHANOR_VLLM_EMBEDDING_URL"),
    )
    reranker_url: str = Field(
        default="http://192.168.1.189:8003",
        validation_alias=AliasChoices("ATHANOR_VLLM_RERANKER_URL"),
    )

    agent_server_url: str = Field(
        default="http://192.168.1.244:9000",
        validation_alias=AliasChoices("ATHANOR_AGENT_SERVER_URL"),
    )
    dashboard_url: str = Field(
        default="http://192.168.1.225:3001",
        validation_alias=AliasChoices("ATHANOR_DASHBOARD_URL"),
    )
    prometheus_url: str = Field(
        default="http://192.168.1.203:9090",
        validation_alias=AliasChoices("ATHANOR_PROMETHEUS_URL"),
    )
    grafana_url: str = Field(
        default="http://192.168.1.203:3000",
        validation_alias=AliasChoices("ATHANOR_GRAFANA_URL"),
    )
    qdrant_url: str = Field(
        default="http://192.168.1.244:6333",
        validation_alias=AliasChoices("ATHANOR_QDRANT_URL"),
    )
    redis_url: str = Field(
        default="redis://192.168.1.203:6379/0",
        validation_alias=AliasChoices("ATHANOR_REDIS_URL"),
    )
    redis_password: str = Field(
        default="",
        validation_alias=AliasChoices("ATHANOR_REDIS_PASSWORD"),
    )
    subscription_policy_path: str = Field(
        default="",
        validation_alias=AliasChoices("ATHANOR_SUBSCRIPTION_POLICY_PATH"),
    )
    neo4j_url: str = Field(
        default="http://192.168.1.203:7474",
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
    sabnzbd_url: str = Field(
        default="http://192.168.1.203:8080",
        validation_alias=AliasChoices("ATHANOR_SABNZBD_URL"),
    )
    stash_url: str = Field(
        default="http://192.168.1.203:9999",
        validation_alias=AliasChoices("ATHANOR_STASH_URL"),
    )

    comfyui_url: str = Field(
        default="http://192.168.1.225:8188",
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
        default="http://192.168.1.244:8200",
        validation_alias=AliasChoices("ATHANOR_SPEACHES_URL"),
    )
    gpu_orchestrator_url: str = Field(
        default="http://192.168.1.244:9200",
        validation_alias=AliasChoices("ATHANOR_GPU_ORCHESTRATOR_URL"),
    )
    langfuse_url: str = Field(
        default="http://192.168.1.203:3030",
        validation_alias=AliasChoices("ATHANOR_LANGFUSE_URL"),
    )

    miniflux_url: str = Field(
        default="http://192.168.1.203:8070",
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
        default="http://192.168.1.203:8880",
        validation_alias=AliasChoices("ATHANOR_NTFY_URL"),
    )
    ntfy_topic: str = Field(
        default="athanor",
        validation_alias=AliasChoices("ATHANOR_NTFY_TOPIC"),
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
