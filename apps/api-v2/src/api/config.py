from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://noshiro:qwert54321@127.0.0.1:5432/noshiro_db"
    legacy_api_base_url: str = "http://127.0.0.1:8008"
    ai_base_url: str = Field(
        default="",
        validation_alias=AliasChoices("AI_AGENT_API_BASE_URL", "AI_BASE_URL"),
    )
    ai_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("AI_AGENT_API_KEY", "AI_API_KEY"),
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
        default="deepseek-flash",
        validation_alias=AliasChoices("AI_FAST_MODEL", "AI_MODEL"),
    )

    @property
    def async_database_url(self) -> str:
        """Return the URL in the form asyncpg expects."""
        for prefix in ("postgresql://", "postgres://"):
            if self.database_url.startswith(prefix):
                return "postgresql+asyncpg://" + self.database_url[len(prefix) :]
        return self.database_url


settings = Settings()
