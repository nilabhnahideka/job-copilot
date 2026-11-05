"""The migrations must exactly match the table definitions in app/db.py, and must
never try to touch LangGraph's checkpoint tables (which share the Postgres database)."""

from alembic import command
from alembic.config import Config

from app.db import BACKEND_DIR


def test_migrations_match_models_and_ignore_checkpoint_tables(client):
    # `client` has started the app: migrations ran and, on Postgres, LangGraph
    # created its checkpoint tables in the same database.
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    cfg.attributes["configure_logger"] = False
    command.check(cfg)  # raises if a new migration would be generated
