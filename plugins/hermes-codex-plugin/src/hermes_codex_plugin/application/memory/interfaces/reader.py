from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, final

from hermes_codex_plugin.domain.memory.entities import MemoryEntry


@final
class MemoryReader(Protocol):
    @property
    def db_path(self) -> Path: ...

    async def search(
        self,
        query: str,
        *,
        limit: int = 5,
        cwd: Optional[str] = None,
        scope: Optional[str] = None,
        kinds: Optional[List[str]] = None,
        exclude_kinds: Optional[List[str]] = None,
    ) -> List[MemoryEntry]: ...

    async def recent(
        self,
        *,
        limit: int = 20,
        kind: Optional[str] = None,
    ) -> List[MemoryEntry]: ...

    async def stats(self) -> Dict[str, Any]: ...
