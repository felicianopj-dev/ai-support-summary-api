import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "AI Support Summary API")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/support_summary",
    )
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")


settings = Settings()
