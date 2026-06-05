from typing import Iterable

from hermes_codex_plugin.application.memory.dto import MemoryEntryDTO


def format_entries(
    entries: Iterable[MemoryEntryDTO],
    *,
    max_chars: int = 3000,
    heading: str = "Hermes Codex Plugin recalled relevant local memory. Use it only when it helps.",
) -> str:
    lines = [heading]
    for entry in entries:
        content = " ".join(entry.content.split())
        block = (
            "- #{id} [{kind}/{scope}] {content} " "(source={source}, session={session})"
        ).format(
            id=entry.id,
            kind=entry.kind,
            scope=entry.scope,
            content=content,
            source=entry.source or "local",
            session=entry.session_id or "unknown",
        )
        lines.append(block)
        if len("\n".join(lines)) >= max_chars:
            break
    text = "\n".join(lines)
    if len(text) > max_chars:
        return text[: max_chars - 20].rstrip() + "\n...[truncated]"
    return text


def format_search_results(entries: Iterable[MemoryEntryDTO]) -> str:
    lines = []
    for entry in entries:
        lines.append(
            "#{id} [{kind}/{scope}] {created_at} session={session} cwd={cwd}\n{content}".format(
                id=entry.id,
                kind=entry.kind,
                scope=entry.scope,
                created_at=entry.created_at,
                session=entry.session_id or "unknown",
                cwd=entry.cwd or "global",
                content=entry.content,
            )
        )
    return "\n\n".join(lines) if lines else "No matching memories."
