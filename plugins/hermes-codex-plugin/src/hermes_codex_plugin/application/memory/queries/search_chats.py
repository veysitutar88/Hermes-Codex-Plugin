from dataclasses import dataclass
from typing import List

from hermes_codex_plugin.application.memory.dto import MemoryEntryDTO
from hermes_codex_plugin.application.memory.interfaces import MemoryReader
from hermes_codex_plugin.application.memory.mapper import MemoryEntryMapper


@dataclass(frozen=True)
class SearchChats:
    query: str
    limit: int = 5


class SearchChatsHandler:
    def __init__(
        self,
        memory_reader: MemoryReader,
        memory_mapper: MemoryEntryMapper,
    ) -> None:
        self._memory_reader = memory_reader
        self._memory_mapper = memory_mapper

    async def __call__(self, query: SearchChats) -> List[MemoryEntryDTO]:
        entries = await self._memory_reader.search(
            query.query, limit=query.limit, cwd=None
        )
        return [self._memory_mapper.to_dto(entry) for entry in entries]
