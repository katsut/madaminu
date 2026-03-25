from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://localhost:5432/madaminu"
    openai_api_key: str = ""
    debug: bool = False
    testing: bool = False

    model_config = {"env_prefix": "MADAMINU_"}


settings = Settings()
