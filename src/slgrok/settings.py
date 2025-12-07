"""Application settings using pydantic-settings."""

from pydantic import HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_prefix="SLGROK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    base_url: HttpUrl = HttpUrl("http://127.0.0.1:4040")


# Global settings instance
settings = Settings()
