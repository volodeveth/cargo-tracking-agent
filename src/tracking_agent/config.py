from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    track_trace_timeout: int = 20
    source_retries: int = 2
    max_concurrency: int = 3

    llm_enabled: bool = False
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "openai/gpt-4o-mini"
    llm_api_key: str = ""

    cargoai_api_key: str = ""

    sheets_spreadsheet_id: str = ""
    sheets_credentials_path: str = ""

    webhook_url: str = ""
    webhook_secret: str = ""

    recheck_enabled: bool = False
    recheck_interval_minutes: int = 30

    cache_ttl_minutes: int = 60
    db_path: str = "data/tracking.db"
    debug_artifacts: bool = False
    use_fixtures: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
