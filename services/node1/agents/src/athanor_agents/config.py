from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    vllm_base_url: str = "http://localhost:8000/v1"
    vllm_model: str = "/models/Qwen3-32B-AWQ"
    prometheus_url: str = "http://192.168.1.203:9090"
    host: str = "0.0.0.0"
    port: int = 9000

    sonarr_api_key: str = ""
    radarr_api_key: str = ""
    tautulli_api_key: str = ""
    ha_token: str = ""

    model_config = {"env_prefix": "ATHANOR_"}


settings = Settings()
