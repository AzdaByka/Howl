"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Howl API"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    frontend_url: str = "http://localhost:5173"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    database_url: str = "postgresql+psycopg://howl:howl@localhost:5432/howl"

    session_cookie_name: str = "howl_session"
    csrf_cookie_name: str = "howl_csrf"
    session_ttl_days: int = 30
    session_secret: SecretStr = SecretStr("change-me")
    cookie_secure: bool = False

    max_members_per_community: int = 5000
    max_participants_per_voice_channel: int = 8
    invite_ttl_days: int = 7

    media_service_url: str = "http://localhost:8081"
    media_internal_token: SecretStr = SecretStr("change-me-media-token")
    media_timeout_seconds: float = 5.0

    yandex_client_id: str = ""
    yandex_client_secret: SecretStr = SecretStr("")
    yandex_authorize_url: str = "https://oauth.yandex.com/authorize"
    yandex_token_url: str = "https://oauth.yandex.com/token"
    yandex_user_info_url: str = "https://login.yandex.ru/info"
    yandex_redirect_uri: str = "http://localhost:8000/api/v1/auth/yandex/callback"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
