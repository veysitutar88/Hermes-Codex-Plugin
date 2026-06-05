from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_codex_plugin.domain.memory.entities import MemoryEntry
from hermes_codex_plugin.infrastructure.db.gateways.base import SQLAlchemyGateway
from hermes_codex_plugin.infrastructure.db.gateways.memory.common import (
    add_kind_filters,
    entry_from_row,
    tokens_for_query,
)
from hermes_codex_plugin.infrastructure.db.models.memory import (
    MEMORY_ENTRIES_TABLE,
    MEMORY_META_TABLE,
)


class MemoryReaderGateway(SQLAlchemyGateway):
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

    async def search(
        self,
        query: str,
        *,
        limit: int = 5,
        cwd: Optional[str] = None,
        scope: Optional[str] = None,
        kinds: Optional[List[str]] = None,
        exclude_kinds: Optional[List[str]] = None,
    ) -> List[MemoryEntry]:
        tokens = list(tokens_for_query(query))
        if not tokens:
            return []
        if await self.has_fts():
            try:
                return await self._search_fts(
                    tokens,
                    limit=limit,
                    cwd=cwd,
                    scope=scope,
                    kinds=kinds,
                    exclude_kinds=exclude_kinds,
                )
            except OperationalError:
                pass
        return await self._search_like(
            tokens,
            limit=limit,
            cwd=cwd,
            scope=scope,
            kinds=kinds,
            exclude_kinds=exclude_kinds,
        )

    async def recent(
        self,
        *,
        limit: int = 20,
        kind: Optional[str] = None,
    ) -> List[MemoryEntry]:
        stmt = select(MEMORY_ENTRIES_TABLE)
        if kind:
            stmt = stmt.where(MEMORY_ENTRIES_TABLE.c.kind == kind)
        stmt = stmt.order_by(MEMORY_ENTRIES_TABLE.c.id.desc()).limit(limit)
        result = await self._session.execute(stmt)
        rows = result.mappings().all()
        return [entry_from_row(row) for row in rows]

    async def stats(self) -> Dict[str, Any]:
        total = await self._session.scalar(
            select(func.count()).select_from(MEMORY_ENTRIES_TABLE)
        )
        by_kind_result = await self._session.execute(
            select(MEMORY_ENTRIES_TABLE.c.kind, func.count().label("c"))
            .group_by(MEMORY_ENTRIES_TABLE.c.kind)
            .order_by(text("c DESC"))
        )
        by_kind = by_kind_result.mappings().all()
        return {
            "db_path": str(self.db_path),
            "fts5": await self.has_fts(),
            "total_entries": int(total or 0),
            "by_kind": {row["kind"]: int(row["c"]) for row in by_kind},
        }

    async def _search_fts(
        self,
        tokens: List[str],
        *,
        limit: int,
        cwd: Optional[str],
        scope: Optional[str],
        kinds: Optional[List[str]],
        exclude_kinds: Optional[List[str]],
    ) -> List[MemoryEntry]:
        match_query = " OR ".join(
            '"{}"'.format(token.replace('"', '""')) for token in tokens
        )
        filters = ["entries_fts MATCH :match_query"]
        params: Dict[str, Any] = {"match_query": match_query, "limit": limit}
        if cwd:
            filters.append("(e.cwd = :cwd OR e.cwd = '')")
            params["cwd"] = cwd
        if scope:
            filters.append("e.scope = :scope")
            params["scope"] = scope
        add_kind_filters(filters, params, "e.kind", kinds, exclude_kinds)
        sql = """
            SELECT e.*
            FROM entries_fts
            JOIN entries e ON e.id = entries_fts.rowid
            WHERE {where}
            ORDER BY bm25(entries_fts), e.id DESC
            LIMIT :limit
        """.format(
            where=" AND ".join(filters)
        )
        result = await self._session.execute(text(sql), params)
        rows = result.mappings().all()
        return [entry_from_row(row) for row in rows]

    async def _search_like(
        self,
        tokens: List[str],
        *,
        limit: int,
        cwd: Optional[str],
        scope: Optional[str],
        kinds: Optional[List[str]],
        exclude_kinds: Optional[List[str]],
    ) -> List[MemoryEntry]:
        clauses = []
        params: Dict[str, Any] = {"limit": limit}
        for index, token in enumerate(tokens):
            name = "token_{}".format(index)
            clauses.append("content LIKE :{}".format(name))
            params[name] = "%{}%".format(token)
        filters = ["(" + " OR ".join(clauses) + ")"]
        if cwd:
            filters.append("(cwd = :cwd OR cwd = '')")
            params["cwd"] = cwd
        if scope:
            filters.append("scope = :scope")
            params["scope"] = scope
        add_kind_filters(filters, params, "kind", kinds, exclude_kinds)
        sql = """
            SELECT * FROM entries
            WHERE {where}
            ORDER BY id DESC
            LIMIT :limit
        """.format(
            where=" AND ".join(filters)
        )
        result = await self._session.execute(text(sql), params)
        rows = result.mappings().all()
        return [entry_from_row(row) for row in rows]
