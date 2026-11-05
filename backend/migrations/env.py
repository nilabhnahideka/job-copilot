"""Alembic environment: tells Alembic which database to change and what the tables should look like.

- The database URL comes from app settings (DATABASE_URL), the same one the API uses.
- The target schema is the SQLModel tables defined in app/db.py.
"""

from logging.config import fileConfig

from alembic import context
from sqlmodel import SQLModel

import app.db  # noqa: F401  (registers the tables on SQLModel.metadata)
from app.db import get_engine

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = SQLModel.metadata


def include_name(name, type_, parent_names) -> bool:
    """Only manage our own tables.

    LangGraph creates its checkpoint tables (checkpoints, checkpoint_blobs, ...) in the
    same Postgres database. Without this filter, autogenerate would see them as
    "not in the models" and write a migration that DROPS them, deleting every saved
    agent run.
    """
    if type_ == "table":
        return name in target_metadata.tables
    return True


def run_migrations_offline() -> None:
    """Write the SQL to stdout instead of running it (`alembic upgrade head --sql`)."""
    from app.config import get_settings

    context.configure(
        url=get_settings().sqlalchemy_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        include_name=include_name,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with get_engine().connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # SQLite can't ALTER most columns; batch mode recreates the table instead.
            render_as_batch=True,
            include_name=include_name,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
