from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from pytimeparse2 import parse

class Settings(BaseSettings):
    MONGO_URI: str
    MONGO_DB_NAME: str
    ACCESS_TOKEN_SECRET: str
    ACCESS_TOKEN_TTL: int
    REFRESH_TOKEN_SECRET: str
    REFRESH_TOKEN_TTL: int
    REFRESH_TOKEN_ALGORITHM: str
    ACCESS_TOKEN_ALGORITHM: str
    ENV: str
    GOOGLE_API_KEY: str
    REFRESH_TOKEN_ALGORITHM: str
    ACCESS_TOKEN_ALGORITHM: str
    DEEPGRAM_API_KEY: str
    SUPABASE_KEY: str
    SUPABASE_URL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )
    @field_validator(
        "ACCESS_TOKEN_TTL",
        "REFRESH_TOKEN_TTL",
        mode="before"
    )
    @classmethod
    def parse_duration(cls, value):

        if isinstance(value, int):
            return value

        parsed = parse(value)

        if parsed is None:
            raise ValueError(
                f"Invalid duration format: {value}"
            )

        return parsed


settings = Settings()
