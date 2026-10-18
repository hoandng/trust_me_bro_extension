from pydantic_settings import BaseSettings, SettingsConfigDict

import os
env_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))

class Settings(BaseSettings):
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    tavily_api_key: str = ""
    tavily_include_domains: list[str] = []
    tavily_exclude_domains: list[str] = []
    factcheck_api_key: str = ""
    extension_api_key: str = ""
    allowed_origins: str = ""
    
    rate_limit_per_minute_ip: int = 10
    rate_limit_per_day_key: int = 100
    daily_analyze_limit_global: int = 1000
    max_body_size_bytes: int = 8192
    
    env: str = "development"

    model_config = SettingsConfigDict(env_file=env_path, env_file_encoding="utf-8-sig", extra="ignore")

settings = Settings()
