from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    redis_url: str = Field(
        default="redis://192.168.1.203:6379/0",
        validation_alias=AliasChoices("GPU_ORCH_REDIS_URL", "ATHANOR_REDIS_URL"),
    )
    port: int = Field(default=9200, validation_alias=AliasChoices("GPU_ORCH_PORT"))
    host: str = Field(default="0.0.0.0", validation_alias=AliasChoices("GPU_ORCH_HOST"))

    # Node IPs
    node1_ip: str = Field(
        default="192.168.1.244",
        validation_alias=AliasChoices("GPU_ORCH_NODE1_IP", "ATHANOR_NODE1_HOST"),
    )
    node2_ip: str = Field(
        default="192.168.1.225",
        validation_alias=AliasChoices("GPU_ORCH_NODE2_IP", "ATHANOR_NODE2_HOST"),
    )

    # vLLM endpoints (for sleep/wake management)
    vllm_node1_url: str = Field(
        default="http://192.168.1.244:8000",
        validation_alias=AliasChoices("GPU_ORCH_VLLM_NODE1_URL", "ATHANOR_VLLM_COORDINATOR_URL"),
    )
    vllm_node1_embed_url: str = Field(
        default="http://192.168.1.189:8001",
        validation_alias=AliasChoices(
            "GPU_ORCH_VLLM_NODE1_EMBED_URL",
            "GPU_ORCH_VLLM_EMBEDDING_URL",
            "ATHANOR_VLLM_EMBEDDING_URL",
        ),
    )
    vllm_node2_url: str = Field(
        default="http://192.168.1.225:8000",
        validation_alias=AliasChoices("GPU_ORCH_VLLM_NODE2_URL", "ATHANOR_VLLM_WORKER_URL"),
    )

    # DCGM-exporter endpoints (GPU metrics)
    dcgm_node1_url: str = Field(
        default="http://192.168.1.244:9400",
        validation_alias=AliasChoices("GPU_ORCH_DCGM_NODE1_URL"),
    )
    dcgm_node2_url: str = Field(
        default="http://192.168.1.225:9400",
        validation_alias=AliasChoices("GPU_ORCH_DCGM_NODE2_URL"),
    )

    # Prometheus (historical data)
    prometheus_url: str = Field(
        default="http://192.168.1.203:9090",
        validation_alias=AliasChoices("GPU_ORCH_PROMETHEUS_URL", "ATHANOR_PROMETHEUS_URL"),
    )


settings = Settings()
