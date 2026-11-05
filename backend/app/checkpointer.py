"""Where the agent saves its progress (LangGraph "checkpointer").

After every step the agent's state is saved, keyed by the application's
`thread_id`. That is what lets a run pause for your review and continue in a
later request, even after the server restarts.

- Postgres (production): checkpoints go in the same database as everything else.
- SQLite (local development): a separate file, CHECKPOINT_DB_PATH.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from langgraph.checkpoint.base import BaseCheckpointSaver

from app.config import Settings


@contextmanager
def open_checkpointer(settings: Settings) -> Iterator[BaseCheckpointSaver]:
    if settings.is_postgres:
        from langgraph.checkpoint.postgres import PostgresSaver
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool

        # A pool, because FastAPI handles requests on several threads at once.
        # These connection options are the ones PostgresSaver requires.
        with ConnectionPool(
            settings.psycopg_url,
            min_size=1,
            max_size=5,
            kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
            # Free hosted Postgres suspends idle databases; check a connection is alive before using it.
            check=ConnectionPool.check_connection,
        ) as pool:
            saver = PostgresSaver(pool)
            saver.setup()  # creates LangGraph's own checkpoint tables if missing
            yield saver
    else:
        from langgraph.checkpoint.sqlite import SqliteSaver

        Path(settings.checkpoint_db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(settings.checkpoint_db_path, check_same_thread=False)
        try:
            yield SqliteSaver(conn)
        finally:
            conn.close()
