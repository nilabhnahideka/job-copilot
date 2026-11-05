"""App settings, read from environment variables or a `.env` file.

Every setting can be overridden with an env var of the same name in upper case
(e.g. OPENAI_MODEL=gpt-4o). See `.env.example` for the full list."""

from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Also export .env into os.environ so LangSmith tracing (LANGSMITH_*) picks it up.
load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.2

    database_url: str = "sqlite:///./data/copilot.db"
    checkpoint_db_path: str = "./data/checkpoints.db"

    # Comma-separated list of allowed frontend origins
    cors_origins: str = "http://localhost:3000"

    # Agent behaviour
    max_tailor_attempts: int = 2
    max_resume_chars: int = 20_000
    max_job_chars: int = 15_000

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
