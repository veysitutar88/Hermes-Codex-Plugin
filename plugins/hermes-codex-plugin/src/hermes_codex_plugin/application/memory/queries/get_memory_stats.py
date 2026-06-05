from hermes_codex_plugin.application.memory.dto import MemoryStatsDTO
from hermes_codex_plugin.application.memory.interfaces import MemoryReader
from hermes_codex_plugin.application.memory.mapper import MemoryStatsMapper


class GetMemoryStatsHandler:
    def __init__(
        self,
        memory_reader: MemoryReader,
        stats_mapper: MemoryStatsMapper,
    ) -> None:
        self._memory_reader = memory_reader
        self._stats_mapper = stats_mapper

    async def __call__(self) -> MemoryStatsDTO:
        return self._stats_mapper.to_dto(await self._memory_reader.stats())
