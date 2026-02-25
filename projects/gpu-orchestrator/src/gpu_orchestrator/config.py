from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str = "redis://192.168.1.203:6379/0"
    port: int = 9200
    host: str = "0.0.0.0"

    # Node IPs
    node1_ip: str = "192.168.1.244"
    node2_ip: str = "192.168.1.225"

    # vLLM endpoints (for sleep/wake management)
    vllm_node1_url: str = "http://192.168.1.244:8000"
    vllm_node1_embed_url: str = "http://192.168.1.244:8001"
    vllm_node2_url: str = "http://192.168.1.225:8000"

    # DCGM-exporter endpoints (GPU metrics)
    dcgm_node1_url: str = "http://192.168.1.244:9400"
    dcgm_node2_url: str = "http://192.168.1.225:9400"

    # Prometheus (historical data)
    prometheus_url: str = "http://192.168.1.203:9090"

    model_config = {"env_prefix": "GPU_ORCH_"}


settings = Settings()
