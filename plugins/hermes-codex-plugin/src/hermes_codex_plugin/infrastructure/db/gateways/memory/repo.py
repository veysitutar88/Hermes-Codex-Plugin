import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional, cast

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_codex_plugin.domain.memory.entities import MemoryEntry
from hermes_codex_plugin.infrastructure.db.gateways.base import SQLAlchemyGateway
from hermes_codex_plugin.infrastructure.db.models.memory import (
    MEMORY_ENTRIES_TABLE,
    MEMORY_META_TABLE,
)


class MemoryRepoGateway(SQLAlchemyGateway):
    def __init__(self, session: AsyncSession, db_path: Path):
        super().__init__(session)
        self._db_path = Path(db_path).expanduser()

    @property
    def db_path(self) -> Path:
        return self._db_path

    async def has_fts(self) -> bool:
        stmt = select(MEMORY_META_TABLE.c.value).where(
            MEMORY_META_TABLE.c.key == "fts5"
        )
        value = await self._session.scalar(stmt)
        return value == "1"

    async def add_entry(
        self,
        content: str,
        *,
        kind: str = "memory",
        scope: str = "global",
        source: str = "",
        session_id: str = "",
        turn_id: str = "",
        cwd: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        clean_content = MemoryEntry.redact_content(content.strip())
        if not clean_content:
            raise ValueError("content must not be empty")
        metadata = metadata or {}
        created_at = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        fingerprint = self._fingerprint(kind, session_id, turn_id, clean_content)
        metadata_json = json.dumps(metadata, ensure_ascii=True, sort_keys=True)
        use_fts = await self.has_fts()
        existing_id = await self._session.scalar(
            select(MEMORY_ENTRIES_TABLE.c.id).where(
                MEMORY_ENTRIES_TABLE.c.fingerprint == fingerprint
            )
        )
        if existing_id is not None:
            return int(existing_id)

        stmt = MEMORY_ENTRIES_TABLE.insert().values(
            kind=kind,
            scope=scope,
            source=source,
            session_id=session_id,
            turn_id=turn_id,
            cwd=cwd,
            content=clean_content,
            metadata_json=metadata_json,
            fingerprint=fingerprint,
            created_at=created_at,
        )
        result = await self._session.execute(stmt)
        inserted_primary_key = cast(Any, result).inserted_primary_key
        entry_id = int(inserted_primary_key[0])

        if use_fts:
            await self._session.execute(
                text(
                    """
                    INSERT INTO entries_fts(rowid, content, kind, scope, source)
                    VALUES (:entry_id, :content, :kind, :scope, :source)
                    """
                ),
                {
                    "entry_id": entry_id,
                    "content": clean_content,
                    "kind": kind,
                    "scope": scope,
                    "source": source,
                },
            )
        await self._session.flush()
        return entry_id

    async def delete_entry(self, entry_id: int) -> bool:
        row_id = await self._session.scalar(
            select(MEMORY_ENTRIES_TABLE.c.id).where(
                MEMORY_ENTRIES_TABLE.c.id == entry_id
            )
        )
        if row_id is None:
            return False
        if await self.has_fts():
            await self._session.execute(
                text("DELETE FROM entries_fts WHERE rowid = :entry_id"),
                {"entry_id": entry_id},
            )
        await self._session.execute(
            MEMORY_ENTRIES_TABLE.delete().where(MEMORY_ENTRIES_TABLE.c.id == entry_id)
        )
        await self._session.flush()
        return True

    @staticmethod
    def _fingerprint(kind: str, session_id: str, turn_id: str, content: str) -> str:
        identity = "\0".join([kind, session_id, turn_id, content])
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()
