from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./resume_screening.db"
    upload_dir: Path = Path("./data/uploads")
    max_upload_bytes: int = 10 * 1024 * 1024
    max_batch_files: int = 50
    evaluation_provider: str = "heuristic"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_base_url: str | None = None
    resume_retention_days: int = 30

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
