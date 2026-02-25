from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LiteLLM proxy is the single entry point for all inference
    llm_base_url: str = "http://192.168.1.203:4000/v1"
    llm_api_key: str = "sk-athanor-litellm-2026"
    llm_model: str = "reasoning"  # LiteLLM alias → Qwen3-32B-AWQ on Node 1
    llm_model_fast: str = "fast"  # LiteLLM alias → Qwen3-14B on Node 2

    # Legacy direct vLLM access (for tools that need to check vLLM status)
    vllm_node1_url: str = "http://192.168.1.244:8000/v1"
    vllm_node2_url: str = "http://192.168.1.225:8000/v1"
    vllm_embedding_url: str = "http://192.168.1.244:8001/v1"

    # Qdrant vector database
    qdrant_url: str = "http://192.168.1.244:6333"

    # Redis (GWT workspace + GPU orchestrator state)
    redis_url: str = "redis://192.168.1.203:6379/0"

    prometheus_url: str = "http://192.168.1.203:9090"
    host: str = "0.0.0.0"
    port: int = 9000

    sonarr_api_key: str = ""
    radarr_api_key: str = ""
    tautulli_api_key: str = ""

    ha_token: str = ""

    model_config = {"env_prefix": "ATHANOR_"}


settings = Settings()
