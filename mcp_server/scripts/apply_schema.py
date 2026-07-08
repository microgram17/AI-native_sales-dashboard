"""Apply schema.sql to the database.

Usage:
    uv run python -m scripts.apply_schema
"""

from pathlib import Path

from app.db.connection import get_connection


MCP_SERVER_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = MCP_SERVER_ROOT / "app" / "db" / "schema.sql"


def main() -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)

    print(f"Schema applied from {SCHEMA_PATH.relative_to(MCP_SERVER_ROOT)}")


if __name__ == "__main__":
    main()