from dataclasses import dataclass
from typing import Any, Dict

from hermes_codex_plugin.domain.common.entity import Entity
from hermes_codex_plugin.domain.memory.redaction import redact
from hermes_codex_plugin.domain.memory.value_objects import (
    MemoryContent,
    MemoryCreatedAt,
    MemoryCwd,
    MemoryEntryId,
    MemoryKind,
    MemoryMetadata,
    MemoryScope,
    MemorySessionId,
    MemorySource,
    MemoryTurnId,
)


@dataclass(frozen=True)
class MemoryEntry(Entity):
    entry_id: MemoryEntryId
    memory_kind: MemoryKind
    memory_scope: MemoryScope
    memory_source: MemorySource
    session: MemorySessionId
    turn: MemoryTurnId
    current_working_directory: MemoryCwd
    body: MemoryContent
    meta: MemoryMetadata
    created_time: MemoryCreatedAt

    @staticmethod
    def redact_content(content: str) -> str:
        return redact(content)

    @classmethod
    def from_raw(
        cls,
        *,
        id: int,
        kind: str,
        scope: str,
        source: str,
        session_id: str,
        turn_id: str,
        cwd: str,
        content: str,
        metadata: Dict[str, Any],
        created_at: str,
    ) -> "MemoryEntry":
        return cls(
            entry_id=MemoryEntryId(id),
            memory_kind=MemoryKind(kind),
            memory_scope=MemoryScope(scope),
            memory_source=MemorySource(source),
            session=MemorySessionId(session_id),
            turn=MemoryTurnId(turn_id),
            current_working_directory=MemoryCwd(cwd),
            body=MemoryContent(cls.redact_content(content)),
            meta=MemoryMetadata(metadata),
            created_time=MemoryCreatedAt(created_at),
        )
