from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg import Connection
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from sales_db.settings import settings


def get_engine() -> Engine:
    """Create a SQLAlchemy engine for database tooling.

    Scripts are short-lived, so a simple engine factory is enough here.
    Runtime services can create their own engines/pools.
    """
    return create_engine(settings.database_url, future=True)


@contextmanager
def get_connection() -> Iterator[Connection]:
    """Open a psycopg3 connection and commit/rollback automatically."""
    with psycopg.connect(settings.psycopg_url) as conn:
        yield conn
