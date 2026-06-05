from dataclasses import dataclass, field
from typing import Any, Dict

from hermes_codex_plugin.application.common.interfaces import UnitOfWork
from hermes_codex_plugin.application.memory.interfaces import MemoryRepo


@dataclass(frozen=True)
class RememberMemory:
    content: str
    kind: str = "memory"
    scope: str = "global"
    source: str = "application"
    session_id: str = ""
    turn_id: str = ""
    cwd: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class RememberMemoryHandler:
    def __init__(self, memory_repo: MemoryRepo, uow: UnitOfWork) -> None:
        self._memory_repo = memory_repo
        self._uow = uow

    async def __call__(self, command: RememberMemory) -> int:
        entry_id = await self._memory_repo.add_entry(
            command.content,
            kind=command.kind,
            scope=command.scope,
            source=command.source,
            session_id=command.session_id,
            turn_id=command.turn_id,
            cwd=command.cwd,
            metadata=command.metadata,
        )
        await self._uow.commit()
        return entry_id
