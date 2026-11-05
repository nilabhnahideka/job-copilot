"""App settings, read from environment variables or a `.env` file.

Every setting can be overridden with an env var of the same name in upper case
(e.g. OPENAI_MODEL=gpt-4o). See `.env.example` for the full list.
"""

from functools import lru_cache

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Also export .env into os.environ so LangSmith tracing (LANGSMITH_*) picks it up.
load_dotenv()

# Only used in development, so the app runs without setup. Production refuses it.
DEV_JWT_SECRET = "dev-only-insecure-secret-change-me-0000000000"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # "development" or "production". Production turns on stricter checks.
    environment: str = "development"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.2

    # SQLite file locally; a Postgres URL (e.g. from Neon) in production.
    # Both "postgres://" and "postgresql://" URLs are accepted.
    database_url: str = "sqlite:///./data/copilot.db"
    # Only used with SQLite. With Postgres, checkpoints go in the same database.
    checkpoint_db_path: str = "./data/checkpoints.db"

    # Signs login tokens. Must be a long random string in production:
    #   python -c "import secrets; print(secrets.token_urlsafe(48))"
    jwt_secret: str = DEV_JWT_SECRET
    jwt_expire_days: int = 7

    # Comma-separated list of allowed frontend origins
    cors_origins: str = "http://localhost:3000"

    # Agent behaviour
    max_tailor_attempts: int = 2
    max_resume_chars: int = 20_000
    max_job_chars: int = 15_000

    @field_validator("jwt_secret")
    @classmethod
    def _blank_secret_means_dev_default(cls, v: str) -> str:
        # `JWT_SECRET=` left empty in .env should behave like "not set".
        return v.strip() or DEV_JWT_SECRET

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith(("postgres://", "postgresql://", "postgresql+"))

    @property
    def sqlalchemy_url(self) -> str:
        """URL for SQLAlchemy, which needs the driver name (psycopg 3) spelled out."""
        if not self.is_postgres:
            return self.database_url
        rest = self.database_url.split("://", 1)[1]
        return f"postgresql+psycopg://{rest}"

    @property
    def psycopg_url(self) -> str:
        """Plain libpq URL, as the LangGraph Postgres checkpointer expects."""
        rest = self.database_url.split("://", 1)[1]
        return f"postgresql://{rest}"

    def validate_for_production(self) -> None:
        """Fail fast on settings that are unsafe outside your own computer."""
        if self.environment != "production":
            return
        problems = []
        if self.jwt_secret == DEV_JWT_SECRET or len(self.jwt_secret) < 32:
            problems.append("JWT_SECRET must be set to a random string of at least 32 characters")
        if not self.is_postgres:
            problems.append("DATABASE_URL must point to Postgres (local files are wiped on Render)")
        if not self.openai_api_key:
            problems.append("OPENAI_API_KEY is not set")
        if problems:
            raise RuntimeError("Unsafe production settings:\n- " + "\n- ".join(problems))


@lru_cache
def get_settings() -> Settings:
    return Settings()
