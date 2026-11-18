import os
from pathlib import Path

from pydantic import BaseModel, Field, IPvAnyNetwork
from pydantic_settings import BaseSettings, SettingsConfigDict

env_path = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
)
MAX_SEARCH_QUERIES = 2
BACKEND_ROOT = Path(__file__).resolve().parents[2]


class GeminiTokenPrices(BaseModel):
    input_usd_per_million: float = Field(ge=0, allow_inf_nan=False)
    output_usd_per_million: float = Field(ge=0, allow_inf_nan=False)
    cached_input_usd_per_million: float | None = Field(
        default=None, ge=0, allow_inf_nan=False
    )


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
    admin_api_key: str = ""
    metrics_db_path: Path = BACKEND_ROOT / "data" / "metrics.db"
    gemini_token_prices: dict[str, GeminiTokenPrices] = Field(default_factory=dict)
    tavily_usd_per_credit: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    allowed_origins: str = ""

    rate_limit_per_minute_ip: int = 10
    trust_proxy_headers: bool = False
    trusted_proxy_networks: list[IPvAnyNetwork] = Field(default_factory=list)
    rate_limit_per_day_key: int = 100
    daily_analyze_limit_global: int = 1000
    max_body_size_bytes: int = 8192
    analysis_timeout_seconds: float = Field(default=25.0, gt=0, allow_inf_nan=False)
    cache_high_confidence_ttl_seconds: int = Field(default=86400, ge=0)
    cache_low_confidence_ttl_seconds: int = Field(default=3600, ge=0)
    cache_unverified_ttl_seconds: int = Field(default=900, ge=0)

    env: str = "development"

    model_config = SettingsConfigDict(
        env_file=env_path, env_file_encoding="utf-8-sig", extra="ignore"
    )


settings = Settings()
