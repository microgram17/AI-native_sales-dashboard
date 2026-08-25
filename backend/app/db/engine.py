from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Connection, Engine

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    """Return a single cached synchronous SQLAlchemy engine."""
    settings = get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True, future=True)


@contextmanager
def get_connection() -> Iterator[Connection]:
    """Yield a connection that is always closed when the block exits."""
    connection = get_engine().connect()
    try:
        yield connection
    finally:
        connection.close()
