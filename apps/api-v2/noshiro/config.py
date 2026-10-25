from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://noshiro:qwert54321@127.0.0.1:5432/noshiro_db"
    legacy_api_base_url: str = "http://127.0.0.1:8008"

    @property
    def async_database_url(self) -> str:
        """Return the URL in the form asyncpg expects."""
        for prefix in ("postgresql://", "postgres://"):
            if self.database_url.startswith(prefix):
                return "postgresql+asyncpg://" + self.database_url[len(prefix) :]
        return self.database_url


settings = Settings()
