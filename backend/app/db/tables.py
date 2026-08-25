from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    MetaData,
    Table,
    Text,
    TIMESTAMP,
)


# Minimal SQLAlchemy Core metadata used by backend repositories.
# The authoritative schema and migrations live in the top-level database/
# project; this only mirrors the columns the backend actually reads.
metadata = MetaData()


suppliers = Table(
    "suppliers",
    metadata,
    Column("supplier_id", Text, primary_key=True),
    Column("supplier_name", Text, nullable=False),
    Column("active", Boolean, nullable=False),
)


app_users = Table(
    "app_users",
    metadata,
    Column("user_id", Text, primary_key=True),
    Column("auth_subject", Text, nullable=False, unique=True),
    Column("email", Text, nullable=False, unique=True),
    Column("display_name", Text),
    Column("password_hash", Text),
    Column("account_type", Text, nullable=False),
    Column("active", Boolean, nullable=False),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False),
)


supplier_memberships = Table(
    "supplier_memberships",
    metadata,
    Column(
        "user_id",
        Text,
        ForeignKey("app_users.user_id"),
        primary_key=True,
    ),
    Column("supplier_id", Text, primary_key=True),
    Column("role", Text, nullable=False),
    Column("active", Boolean, nullable=False),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False),
)
