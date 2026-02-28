from functools import lru_cache

from pydantic import AnyHttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """
    Secrets and environment-specific configuration loaded from .env.

    Designed for:
    - Strict validation
    - Testability
    - Production safety
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",           # Allow unknown environment variables
        case_sensitive=False,     # Standardize behavior across OS
    )

    # Slack
    slack_webhook_url: AnyHttpUrl | None = None

    # Email
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None

    # Database
    database_url: str = "sqlite:///sentinelflow.db"

    # Redis (optional)
    redis_url: str | None = None

    # Website default
    default_site_url: AnyHttpUrl | None = None

    # Archive storage
    archive_path: str = "./archive"

    # Observability
    otlp_endpoint: str = "http://localhost:4317"
    metrics_port: int = 9108
    admin_port: int = 9109

    @model_validator(mode="after")
    def validate_https(self) -> "AppSettings":
        if self.slack_webhook_url and self.slack_webhook_url.scheme != "https":
            raise ValueError("Slack webhook URL must use HTTPS.")
        return self

    def validate_required_integrations(self, configured_handlers: list[str]) -> list[str]:
        missing = []
        if "slack_webhook" in configured_handlers and not self.slack_webhook_url:
            missing.append("SLACK_WEBHOOK_URL")
        if "email" in configured_handlers and not all([self.smtp_host, self.smtp_port, self.smtp_from]):
            missing.append("SMTP configuration (HOST, PORT, FROM)")
        return missing


# Lazy-loaded singleton
@lru_cache
def get_settings() -> AppSettings:
    """
    Cached settings loader.
    Ensures single instantiation per process.
    """
    return AppSettings()