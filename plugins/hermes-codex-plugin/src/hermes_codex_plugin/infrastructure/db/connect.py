from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

import hermes_codex_plugin.infrastructure.db.models.memory  # noqa: F401
from hermes_codex_plugin.infrastructure.db.models.base import metadata


def database_url(db_path: Path) -> str:
    path = Path(db_path).expanduser()
    return "sqlite+aiosqlite:///{}".format(path)


def create_engine(db_path: Path) -> AsyncEngine:
    path = Path(db_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_async_engine(database_url(path), poolclass=NullPool)


async def sync_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.execute(text("PRAGMA journal_mode=WAL"))
        await connection.run_sync(metadata.create_all)
        try:
            await connection.execute(
                text(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts
                    USING fts5(
                        content,
                        kind,
                        scope,
                        source,
                        content='entries',
                        content_rowid='id',
                        tokenize='unicode61'
                    )
                    """
                )
            )
            await connection.execute(
                text("INSERT OR REPLACE INTO meta(key, value) VALUES('fts5', '1')")
            )
        except OperationalError:
            await connection.execute(
                text("INSERT OR REPLACE INTO meta(key, value) VALUES('fts5', '0')")
            )


async def memory_session_maker(
    db_path: Path,
) -> async_sessionmaker[AsyncSession]:
    engine = create_engine(db_path)
    await sync_tables(engine)
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,
    )


@asynccontextmanager
async def open_memory_sessionmaker(
    db_path: Path,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_engine(db_path)
    try:
        await sync_tables(engine)
        yield async_sessionmaker(
            engine,
            class_=AsyncSession,
            autoflush=False,
            expire_on_commit=False,
        )
    finally:
        await engine.dispose()


@asynccontextmanager
async def open_memory_session(db_path: Path) -> AsyncIterator[AsyncSession]:
    engine = create_engine(db_path)
    try:
        await sync_tables(engine)
        session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            autoflush=False,
            expire_on_commit=False,
        )
        async with session_maker() as session:
            yield session
    finally:
        await engine.dispose()
