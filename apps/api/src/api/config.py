import json
from typing import Annotated, Any, Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    database_url: str = "postgresql://noshiro@127.0.0.1:5432/noshiro_db"
    redis_cache_url: str = ""
    enable_api_docs: bool = True
    cors_allow_all_origins: bool = False
    cors_allow_credentials: bool = False
    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    avatar_max_upload_size: int = Field(default=10 * 1024 * 1024, gt=0)
    hcaptcha_enabled: bool = False
    hcaptcha_secret_key: str = ""
    hcaptcha_siteverify_url: str = "https://api.hcaptcha.com/siteverify"
    hcaptcha_timeout: float = Field(default=5, gt=0)
    avatar_allowed_content_types: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["image/jpeg", "image/png", "image/webp"]
    )
    ai_base_url: str = Field(
        default="",
        validation_alias=AliasChoices("AI_AGENT_API_BASE_URL", "AI_BASE_URL"),
    )
    ai_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("AI_AGENT_API_KEY", "AI_API_KEY"),
    )
    jwt_secret: str = ""
    access_token_seconds: int = 2 * 60 * 60
    refresh_token_seconds: int = 30 * 24 * 60 * 60
    refresh_cookie_name: str = Field(
        default="noshiro_refresh",
        validation_alias=AliasChoices("REFRESH_COOKIE_NAME", "JWT_REFRESH_COOKIE_NAME"),
    )
    refresh_cookie_path: str = Field(
        default="/api/v1/auth/",
        validation_alias=AliasChoices("REFRESH_COOKIE_PATH", "JWT_REFRESH_COOKIE_PATH"),
    )
    refresh_cookie_domain: str | None = Field(
        default=None,
        validation_alias=AliasChoices("REFRESH_COOKIE_DOMAIN", "JWT_REFRESH_COOKIE_DOMAIN"),
    )
    refresh_cookie_secure: bool = Field(
        default=False,
        validation_alias=AliasChoices("REFRESH_COOKIE_SECURE", "JWT_REFRESH_COOKIE_SECURE"),
    )
    refresh_cookie_samesite: Literal["lax", "strict", "none"] = Field(
        default="lax",
        validation_alias=AliasChoices("REFRESH_COOKIE_SAMESITE", "JWT_REFRESH_COOKIE_SAMESITE"),
    )
    refresh_cookie_max_age: int = Field(
        default=30 * 24 * 60 * 60,
        gt=0,
        validation_alias=AliasChoices("REFRESH_COOKIE_MAX_AGE", "JWT_REFRESH_COOKIE_MAX_AGE"),
    )
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
    mcp_port: int = Field(default=8011, ge=1, le=65535)
    mcp_rate_limit: int = Field(default=60, gt=0)
    mcp_rate_window_seconds: int = Field(default=60, gt=0)

    @field_validator("cors_allowed_origins", "avatar_allowed_content_types", mode="before")
    @classmethod
    def list_values(cls, value: Any) -> Any:
        if isinstance(value, str):
            return json.loads(value) if value.lstrip().startswith("[") else value.split(",")
        return value

    @field_validator("cors_allowed_origins", "avatar_allowed_content_types")
    @classmethod
    def clean_values(cls, value: list[str]) -> list[str]:
        return [origin.strip() for origin in value if origin.strip()]

    @field_validator("avatar_allowed_content_types")
    @classmethod
    def content_types(cls, value: list[str]) -> list[str]:
        return [content_type.lower() for content_type in value]

    @field_validator("refresh_cookie_domain", mode="before")
    @classmethod
    def cookie_domain(cls, value: Any) -> Any:
        return value or None

    @field_validator("refresh_cookie_samesite", mode="before")
    @classmethod
    def cookie_samesite(cls, value: Any) -> Any:
        return value.lower() if isinstance(value, str) else value

    @property
    def async_database_url(self) -> str:
        """Return the URL in the form asyncpg expects."""
        for prefix in ("postgresql://", "postgres://"):
            if self.database_url.startswith(prefix):
                return "postgresql+asyncpg://" + self.database_url[len(prefix) :]
        return self.database_url


settings = Settings()
