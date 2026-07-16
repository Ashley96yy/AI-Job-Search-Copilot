from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "AI Job Search Copilot")
    app_version: str = os.getenv("APP_VERSION", "0.1.0")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./job_search_copilot.db")


settings = Settings()
