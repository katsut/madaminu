from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://localhost:5432/madaminu"
    openai_api_key: str = ""
    debug: bool = False
    testing: bool = False

    model_config = {"env_prefix": "MADAMINU_", "env_file": ".env"}

    @property
    def async_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


settings = Settings()
