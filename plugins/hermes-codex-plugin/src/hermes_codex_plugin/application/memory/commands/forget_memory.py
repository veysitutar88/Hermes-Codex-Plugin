from dataclasses import dataclass

from hermes_codex_plugin.application.common.interfaces import UnitOfWork
from hermes_codex_plugin.application.memory.interfaces import MemoryRepo


@dataclass(frozen=True)
class ForgetMemory:
    entry_id: int


class ForgetMemoryHandler:
    def __init__(self, memory_repo: MemoryRepo, uow: UnitOfWork) -> None:
        self._memory_repo = memory_repo
        self._uow = uow

    async def __call__(self, command: ForgetMemory) -> bool:
        deleted = await self._memory_repo.delete_entry(command.entry_id)
        if deleted:
            await self._uow.commit()
        return deleted
