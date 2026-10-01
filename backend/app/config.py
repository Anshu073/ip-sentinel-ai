"""Application configuration loaded from environment / .env."""

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    serpapi_key: str = ""
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"

    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # 1 hour default — avoids repeat SerpApi spend for identical queries
    cache_ttl_seconds: int = 3600

    # Background watch interval (N hours). Set 0 to disable auto-watch on POST /api/scan
    rescan_interval_hours: int = 6

    whois_timeout_seconds: int = 8
    database_url: str = "sqlite:///./data/scanner.db"

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _stringify_origins(cls, value: object) -> str:
        if isinstance(value, list):
            return ",".join(str(v) for v in value)
        return str(value)

    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
