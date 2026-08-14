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


# Minimal SQLAlchemy Core metadata used by auth_repository.py.
# The authoritative schema and migrations live in the top-level database/ project;
# this only mirrors the columns the backend actually reads.
metadata = MetaData()


app_users = Table(
    "app_users",
    metadata,
    Column("user_id", Text, primary_key=True),
    Column("auth_subject", Text, nullable=False, unique=True),
    Column("email", Text, nullable=False),
    Column("display_name", Text),
    Column("active", Boolean, nullable=False),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False),
)


supplier_memberships = Table(
    "supplier_memberships",
    metadata,
    Column("user_id", Text, ForeignKey("app_users.user_id"), primary_key=True),
    Column("supplier_id", Text, primary_key=True),
    Column("role", Text, nullable=False),
    Column("active", Boolean, nullable=False),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False),
)
