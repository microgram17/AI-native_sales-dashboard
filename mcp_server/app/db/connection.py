import os
from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg import Connection
from psycopg_pool import AsyncConnectionPool


DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/retail_bi"


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def create_pool() -> AsyncConnectionPool:
    return AsyncConnectionPool(
        conninfo=get_database_url(),
        open=False,
    )


@contextmanager
def get_connection() -> Iterator[Connection]:
    """
    Simple synchronous connection helper for scripts.

    Use this for scripts like:
    - apply_schema.py
    - import_demo_data.py

    Use create_pool() for the async MCP server.
    """
    with psycopg.connect(get_database_url()) as conn:
        yield conn