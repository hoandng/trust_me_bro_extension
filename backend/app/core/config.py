from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str = ""
    tavily_api_key: str = ""
    tavily_include_domains: list[str] = []
    tavily_exclude_domains: list[str] = []
    factcheck_api_key: str = ""
    extension_api_key: str = ""
    allowed_origins: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
