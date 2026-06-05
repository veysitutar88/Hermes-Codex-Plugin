import json
import re
from collections.abc import Mapping
from typing import Any, Dict, Iterable, List, Optional

from hermes_codex_plugin.domain.memory.entities import MemoryEntry

TOKEN_RE = re.compile(r"[\w]{2,}", re.UNICODE)


def add_kind_filters(
    filters: List[str],
    params: Dict[str, Any],
    column: str,
    kinds: Optional[List[str]],
    exclude_kinds: Optional[List[str]],
) -> None:
    if kinds:
        placeholders = []
        for index, kind in enumerate(kinds):
            name = "kind_{}".format(index)
            placeholders.append(":{}".format(name))
            params[name] = kind
        filters.append("{} IN ({})".format(column, ", ".join(placeholders)))
    if exclude_kinds:
        placeholders = []
        for index, kind in enumerate(exclude_kinds):
            name = "exclude_kind_{}".format(index)
            placeholders.append(":{}".format(name))
            params[name] = kind
        filters.append("{} NOT IN ({})".format(column, ", ".join(placeholders)))


def tokens_for_query(query: str) -> Iterable[str]:
    seen = set()
    for token in TOKEN_RE.findall(query.lower()):
        if token not in seen:
            seen.add(token)
            yield token
        if len(seen) >= 12:
            break


def entry_from_row(row: Mapping[Any, Any]) -> MemoryEntry:
    try:
        metadata = json.loads(row["metadata_json"])
    except json.JSONDecodeError:
        metadata = {}
    if not isinstance(metadata, dict):
        metadata = {}
    return MemoryEntry.from_raw(
        id=int(row["id"]),
        kind=row["kind"],
        scope=row["scope"],
        source=row["source"],
        session_id=row["session_id"],
        turn_id=row["turn_id"],
        cwd=row["cwd"],
        content=row["content"],
        metadata=metadata,
        created_at=row["created_at"],
    )
