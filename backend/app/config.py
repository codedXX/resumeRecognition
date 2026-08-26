from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    roles_file: Path = Path("./data/roles.json")
    analysis_retention_minutes: int = 30
    workers: int = 1
    max_upload_bytes: int = 10 * 1024 * 1024
    max_batch_files: int = 50
    pending_input_retention_minutes: int = 60
    evaluation_provider: str = "heuristic"
    openai_api_key: str | None = None
    openai_model: str = "qwen-plus"
    openai_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
