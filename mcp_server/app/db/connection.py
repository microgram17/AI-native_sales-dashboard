import os

import psycopg
from psycopg import Connection


DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/retail_bi"


def get_database_url() -> str:
    return os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL


def get_connection() -> Connection:
    database_url = get_database_url()
    print(f"Connecting to database: {mask_database_url(database_url)}")
    return psycopg.connect(database_url)


def mask_database_url(database_url: str) -> str:
    return database_url.replace(":postgres@", ":***@")