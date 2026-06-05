from dataclasses import dataclass
from typing import List, Optional

from hermes_codex_plugin.application.memory.dto import MemoryEntryDTO
from hermes_codex_plugin.application.memory.interfaces import MemoryReader
from hermes_codex_plugin.application.memory.mapper import MemoryEntryMapper


@dataclass(frozen=True)
class SearchMemory:
    query: str
    limit: int = 5
    cwd: Optional[str] = None
    scope: Optional[str] = None
    kinds: Optional[List[str]] = None
    exclude_kinds: Optional[List[str]] = None


class SearchMemoryHandler:
    def __init__(
        self,
        memory_reader: MemoryReader,
        memory_mapper: MemoryEntryMapper,
    ) -> None:
        self._memory_reader = memory_reader
        self._memory_mapper = memory_mapper

    async def __call__(self, query: SearchMemory) -> List[MemoryEntryDTO]:
        entries = await self._memory_reader.search(
            query.query,
            limit=query.limit,
            cwd=query.cwd,
            scope=query.scope,
            kinds=query.kinds,
            exclude_kinds=query.exclude_kinds,
        )
        return [self._memory_mapper.to_dto(entry) for entry in entries]
