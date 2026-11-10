import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

env_path = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
)
MAX_SEARCH_QUERIES = 2


class Settings(BaseSettings):
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.1-flash-lite"
    # Empty list keeps the existing single-model deployment working.
    gemini_models: list[str] = []
    gemini_quota_cooldown_seconds: int = 60

    @property
    def available_gemini_models(self) -> list[str]:
        return list(dict.fromkeys([self.gemini_model, *self.gemini_models]))

    tavily_api_key: str = ""
    tavily_include_domains: list[str] = []
    tavily_exclude_domains: list[str] = []
    factcheck_api_key: str = ""
    search_query_limit: int = Field(
        default=MAX_SEARCH_QUERIES, ge=1, le=MAX_SEARCH_QUERIES
    )
    extension_api_key: str = ""
    allowed_origins: str = ""

    rate_limit_per_minute_ip: int = 10
    rate_limit_per_day_key: int = 100
    daily_analyze_limit_global: int = 1000
    max_body_size_bytes: int = 8192

    env: str = "development"

    model_config = SettingsConfigDict(
        env_file=env_path, env_file_encoding="utf-8-sig", extra="ignore"
    )


settings = Settings()
