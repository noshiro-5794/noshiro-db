from typing import Any, Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://noshiro@127.0.0.1:5432/noshiro_db"
    ai_base_url: str = Field(
        default="",
        validation_alias=AliasChoices("AI_AGENT_API_BASE_URL", "AI_BASE_URL"),
    )
    ai_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("AI_AGENT_API_KEY", "AI_API_KEY"),
    )
    jwt_secret: str = Field(default="", validation_alias=AliasChoices("DJANGO_SECRET_KEY"))
    access_token_seconds: int = 2 * 60 * 60
    refresh_token_seconds: int = 30 * 24 * 60 * 60
    refresh_cookie_name: str = "noshiro_refresh"
    refresh_cookie_path: str = "/api/v1/auth/"
    refresh_cookie_secure: bool = False
    refresh_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    github_client_id: str = Field(
        default="",
        validation_alias=AliasChoices("GITHUB_OAUTH_CLIENT_ID"),
    )
    github_client_secret: str = Field(
        default="",
        validation_alias=AliasChoices("GITHUB_OAUTH_CLIENT_SECRET"),
    )
    ai_model: str = Field(
        default="deepseek-ai/DeepSeek-V4-Flash",
        validation_alias=AliasChoices("AI_FAST_MODEL", "AI_MODEL"),
    )
    ai_reasoning_model: str = Field(
        default="deepseek-ai/DeepSeek-V4-Pro", validation_alias="AI_REASONING_MODEL"
    )
    ai_model_prices: dict[str, Any] = Field(
        default_factory=dict, validation_alias="AI_MODEL_PRICES"
    )
    ai_timeout_seconds: float = Field(default=30, gt=0, validation_alias="AI_AGENT_TIMEOUT")
    ai_max_output_tokens: int = Field(
        default=1024, gt=0, validation_alias="AI_AGENT_MAX_OUTPUT_TOKENS"
    )

    sync_calendar_cron_hour: int = Field(default=3, ge=0, le=23)
    sync_calendar_cron_minute: int = Field(default=30, ge=0, le=59)
    sync_incremental_cron_hour: int = Field(default=4, ge=0, le=23)
    sync_incremental_cron_minute: int = Field(default=0, ge=0, le=59)
    match_candidate_sweep_cron_hours: int = Field(default=4, gt=0)

    mcp_host: str = "127.0.0.1"
    mcp_port: int = Field(default=8010, ge=1, le=65535)
    mcp_rate_limit: int = Field(default=60, gt=0)
    mcp_rate_window_seconds: int = Field(default=60, gt=0)

    @property
    def async_database_url(self) -> str:
        """Return the URL in the form asyncpg expects."""
        for prefix in ("postgresql://", "postgres://"):
            if self.database_url.startswith(prefix):
                return "postgresql+asyncpg://" + self.database_url[len(prefix) :]
        return self.database_url


settings = Settings()
