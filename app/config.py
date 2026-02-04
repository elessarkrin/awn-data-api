from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    awn_api_key: str = ""
    awn_application_key: str = ""
    awn_mac_address: str = ""

    collection_interval_seconds: int = 60
    daily_retention_days: int = 7

    database_url: str = "sqlite+aiosqlite:///./weather.db"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
