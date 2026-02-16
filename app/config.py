from pydantic import field_validator, ConfigDict, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    awn_api_key: str = ""
    awn_application_key: str = ""
    awn_mac_address: str = ""

    collection_interval_seconds: int = 60
    daily_retention_days: int = 365

    backfill_days: int = 365
    backfill_batch_size: int = 288
    backfill_request_delay: float = 1.1

    database_url: str = "sqlite+aiosqlite:///./weather.db"
    cors_allow_origins: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:5174"],
        json_schema_extra={"env": "CORS_ALLOW_ORIGINS"}
    )
    cors_allow_credentials: bool = True
    gzip_minimum_size: int = 500
    gzip_compresslevel: int = 6

    astronomy_api_key: str = ""
    lat: str = ""
    lon: str = ""
    react_build_dir: str = "frontend/dist"

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def parse_cors_allow_origins(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


settings = Settings()
