from sqlalchemy import Column, Integer, Table, Text

from hermes_codex_plugin.infrastructure.db.models.base import metadata

MEMORY_ENTRIES_TABLE = Table(
    "entries",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("kind", Text, nullable=False),
    Column("scope", Text, nullable=False, default="global"),
    Column("source", Text, nullable=False, default=""),
    Column("session_id", Text, nullable=False, default=""),
    Column("turn_id", Text, nullable=False, default=""),
    Column("cwd", Text, nullable=False, default=""),
    Column("content", Text, nullable=False),
    Column("metadata_json", Text, nullable=False, default="{}"),
    Column("fingerprint", Text, nullable=False, unique=True),
    Column("created_at", Text, nullable=False),
)


MEMORY_META_TABLE = Table(
    "meta",
    metadata,
    Column("key", Text, primary_key=True),
    Column("value", Text, nullable=False),
)
