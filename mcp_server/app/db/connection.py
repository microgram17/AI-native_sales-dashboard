import os
from contextlib import asynccontextmanager

import psycopg
from psycopg import Connection
from psycopg_pool import AsyncConnectionPool


DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/retail_bi"


def get_database_url() -> str:
    return os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL


def get_connection() -> Connection:
    database_url = get_database_url()
    print(f"Connecting to database: {mask_database_url(database_url)}")
    return psycopg.connect(database_url)


def mask_database_url(database_url: str) -> str:
    return database_url.replace(":postgres@", ":***@")


class LazyAsyncConnectionPool:
    def __init__(self, conninfo: str):
        self.conninfo = conninfo
        self._pool: AsyncConnectionPool | None = None

    @asynccontextmanager
    async def connection(self):
        if self._pool is None:
            self._pool = AsyncConnectionPool(self.conninfo, open=False)
            await self._pool.open(wait=True)

        async with self._pool.connection() as conn:
            yield conn