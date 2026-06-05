from typing import Iterable, List

from hermes_codex_plugin.application.memory.interfaces import MemoryReader
from hermes_codex_plugin.domain.memory.entities import MemoryEntry

DURABLE_KINDS = ["project_rule", "user_rule", "rule", "summary", "memory"]
RECALL_KINDS = [
    "project_rule",
    "user_rule",
    "rule",
    "summary",
    "memory",
    "assistant",
    "transcript",
]


class MemoryRecallService:
    def __init__(self, memory_reader: MemoryReader) -> None:
        self._memory_reader = memory_reader

    async def recall(self, query: str, *, limit: int, cwd: str) -> List[MemoryEntry]:
        same_cwd_durable = await self._memory_reader.search(
            query,
            limit=max(limit, 8),
            cwd=cwd,
            kinds=DURABLE_KINDS,
        )
        cross_cwd_durable = await self._memory_reader.search(
            query,
            limit=max(limit, 8),
            cwd=None,
            kinds=DURABLE_KINDS,
        )
        same_cwd_supplemental = await self._memory_reader.search(
            query,
            limit=limit,
            cwd=cwd,
            kinds=RECALL_KINDS,
        )
        cross_cwd_supplemental = await self._memory_reader.search(
            query,
            limit=limit,
            cwd=None,
            kinds=RECALL_KINDS,
        )
        return dedupe_entries(
            same_cwd_durable
            + cross_cwd_durable
            + same_cwd_supplemental
            + cross_cwd_supplemental
        )[:limit]

    async def recent_durable(self, *, limit: int) -> List[MemoryEntry]:
        entries: List[MemoryEntry] = []
        for kind in DURABLE_KINDS:
            entries.extend(await self._memory_reader.recent(limit=limit, kind=kind))
        entries.sort(key=lambda entry: entry.entry_id.to_raw(), reverse=True)
        return entries[:limit]


def dedupe_entries(entries: Iterable[MemoryEntry]) -> List[MemoryEntry]:
    seen = set()
    unique: List[MemoryEntry] = []
    for entry in entries:
        entry_id = entry.entry_id.to_raw()
        if entry_id in seen:
            continue
        seen.add(entry_id)
        unique.append(entry)
    return unique
