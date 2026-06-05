import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict

from hermes_codex_plugin.application.common.interfaces import UnitOfWork
from hermes_codex_plugin.application.memory.commands.remember_memory import (
    RememberMemory,
    RememberMemoryHandler,
)
from hermes_codex_plugin.application.memory.interfaces import MemoryReader, MemoryRepo
from hermes_codex_plugin.application.memory.mapper import MemoryEntryMapper
from hermes_codex_plugin.application.memory.recall import (
    MemoryRecallService,
    dedupe_entries,
)
from hermes_codex_plugin.domain.memory.policy import (
    global_memory_policy_context,
    search_hint_context,
)
from hermes_codex_plugin.infrastructure.config import load_settings
from hermes_codex_plugin.infrastructure.db.connect import open_memory_session
from hermes_codex_plugin.infrastructure.db.gateways.memory import (
    MemoryReaderGateway,
    MemoryRepoGateway,
)
from hermes_codex_plugin.infrastructure.logging import logger
from hermes_codex_plugin.presentation.formatting import format_entries


def main(expected_event: str) -> None:
    try:
        event = read_event()
        result = handle_event(event, expected_event=expected_event)
        if result is not None:
            write_stdout(json.dumps(result, ensure_ascii=True))
    except Exception as exc:
        logger.exception("Hermes Codex Plugin hook failed")
        payload = {
            "continue": True,
            "systemMessage": "Hermes Codex Plugin hook failed: {}".format(exc),
        }
        write_stdout(json.dumps(payload, ensure_ascii=True))


def write_stdout(message: str) -> None:
    sys.stdout.write(message)
    if not message.endswith("\n"):
        sys.stdout.write("\n")


def read_event() -> Dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        return {}
    return payload


def handle_event(event: Dict[str, Any], *, expected_event: str) -> Dict[str, Any]:
    return asyncio.run(handle_event_async(event, expected_event=expected_event))


async def handle_event_async(
    event: Dict[str, Any],
    *,
    expected_event: str,
) -> Dict[str, Any]:
    settings = load_settings()
    if settings.disabled:
        return {"continue": True}

    async with open_memory_session(settings.db_path) as session:
        memory_reader = MemoryReaderGateway(session, settings.db_path)
        memory_repo = MemoryRepoGateway(session, settings.db_path)
        name = event.get("hook_event_name") or expected_event
        if expected_event == "SessionStart":
            return await handle_session_start(
                memory_reader,
                event,
                name,
                settings.recall_chars,
            )
        if expected_event == "UserPromptSubmit":
            return await handle_user_prompt_submit(
                memory_reader,
                memory_repo,
                session,
                event,
                name,
                settings.recall_limit,
                settings.recall_chars,
            )
        if expected_event == "Stop":
            return await handle_stop(
                memory_repo,
                session,
                event,
                settings.capture_assistant,
            )
        if expected_event == "PreCompact":
            return await handle_pre_compact(
                memory_repo,
                session,
                event,
                settings.max_capture_chars,
            )
    return {"continue": True}


async def handle_session_start(
    memory_reader: MemoryReader,
    event: Dict[str, Any],
    hook_name: str,
    max_chars: int,
) -> Dict[str, Any]:
    del event
    recent = await memory_reader.recent(limit=5)
    if not recent:
        return {"continue": True}
    memory_mapper = MemoryEntryMapper()
    context = format_entries(
        [memory_mapper.to_dto(entry) for entry in recent],
        max_chars=max_chars,
    )
    return additional_context(hook_name, context)


async def handle_user_prompt_submit(
    memory_reader: MemoryReader,
    memory_repo: MemoryRepo,
    uow: UnitOfWork,
    event: Dict[str, Any],
    hook_name: str,
    limit: int,
    max_chars: int,
) -> Dict[str, Any]:
    prompt = str(event.get("prompt") or "").strip()
    session_id = str(event.get("session_id") or "")
    turn_id = str(event.get("turn_id") or "")
    cwd = str(event.get("cwd") or "")

    if not prompt:
        return {"continue": True}

    recall_service = MemoryRecallService(memory_reader)
    matches = await recall_service.recall(prompt, limit=limit, cwd=cwd)
    standing = await recall_service.recent_durable(limit=3)
    memory_mapper = MemoryEntryMapper()

    remember = RememberMemoryHandler(memory_repo, uow)
    await remember(
        RememberMemory(
            prompt,
            kind="prompt",
            scope="session",
            source="UserPromptSubmit",
            session_id=session_id,
            turn_id=turn_id,
            cwd=cwd,
            metadata={"hook_event_name": hook_name},
        )
    )

    context_parts = [global_memory_policy_context(), search_hint_context(prompt)]
    recalled = dedupe_entries(standing + matches)
    if recalled:
        context_parts.append(
            format_entries(
                [memory_mapper.to_dto(entry) for entry in recalled],
                max_chars=max_chars,
                heading=(
                    "Hermes Codex Plugin durable/relevant memory. Prefer user_rule, "
                    "project_rule, rule, summary, and memory entries over transient "
                    "prompt/assistant history."
                ),
            )
        )
    return additional_context(hook_name, "\n\n".join(context_parts))


async def handle_stop(
    memory_repo: MemoryRepo,
    uow: UnitOfWork,
    event: Dict[str, Any],
    capture_assistant: bool,
) -> Dict[str, Any]:
    if not capture_assistant:
        return {"continue": True}
    message = str(event.get("last_assistant_message") or "").strip()
    if message:
        remember = RememberMemoryHandler(memory_repo, uow)
        await remember(
            RememberMemory(
                message,
                kind="assistant",
                scope="session",
                source="Stop",
                session_id=str(event.get("session_id") or ""),
                turn_id=str(event.get("turn_id") or ""),
                cwd=str(event.get("cwd") or ""),
                metadata={"hook_event_name": event.get("hook_event_name") or "Stop"},
            )
        )
    return {"continue": True}


async def handle_pre_compact(
    memory_repo: MemoryRepo,
    uow: UnitOfWork,
    event: Dict[str, Any],
    max_capture_chars: int,
) -> Dict[str, Any]:
    transcript_path = event.get("transcript_path")
    if not transcript_path:
        return {"continue": True}
    path = Path(str(transcript_path)).expanduser()
    if not path.is_file():
        return {"continue": True}
    content = path.read_text(encoding="utf-8", errors="replace")
    if len(content) > max_capture_chars:
        content = content[-max_capture_chars:]
    if content.strip():
        remember = RememberMemoryHandler(memory_repo, uow)
        await remember(
            RememberMemory(
                content,
                kind="transcript",
                scope="session",
                source=str(path),
                session_id=str(event.get("session_id") or ""),
                turn_id=str(event.get("turn_id") or ""),
                cwd=str(event.get("cwd") or ""),
                metadata={
                    "hook_event_name": event.get("hook_event_name") or "PreCompact",
                    "trigger": event.get("trigger"),
                },
            )
        )
    return {"continue": True}


def additional_context(hook_name: str, context: str) -> Dict[str, Any]:
    return {
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": hook_name,
            "additionalContext": context,
        },
    }
