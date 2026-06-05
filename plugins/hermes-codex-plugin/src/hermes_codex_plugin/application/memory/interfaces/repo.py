from typing import Any, Dict, Optional, Protocol, final


@final
class MemoryRepo(Protocol):
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
    ) -> int: ...

    async def delete_entry(self, entry_id: int) -> bool: ...
