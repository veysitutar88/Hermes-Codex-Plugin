import os
import tempfile
import unittest
from pathlib import Path

from hermes_codex_plugin.infrastructure.config import load_settings
from hermes_codex_plugin.infrastructure.db.connect import open_memory_session
from hermes_codex_plugin.infrastructure.db.gateways.memory import (
    MemoryReaderGateway,
    MemoryRepoGateway,
)
from hermes_codex_plugin.presentation.hooks.controller import handle_event_async


class HookTest(unittest.IsolatedAsyncioTestCase):
    async def add_entry(self, content: str, **kwargs) -> int:
        db_path = load_settings().db_path
        async with open_memory_session(db_path) as session:
            repo = MemoryRepoGateway(session, db_path)
            entry_id = await repo.add_entry(content, **kwargs)
            await session.commit()
            return entry_id

    async def search_entries(self, query: str):
        db_path = load_settings().db_path
        async with open_memory_session(db_path) as session:
            reader = MemoryReaderGateway(session, db_path)
            return await reader.search(query)

    async def total_entries(self) -> int:
        db_path = load_settings().db_path
        async with open_memory_session(db_path) as session:
            reader = MemoryReaderGateway(session, db_path)
            return int((await reader.stats())["total_entries"])

    async def test_user_prompt_submit_captures_and_recalls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["HERMES_CODEX_DB"] = str(Path(tmp) / "memory.sqlite3")
            try:
                await self.add_entry(
                    "Always use DDD boundaries in Python services.",
                    kind="rule",
                )

                payload = {
                    "hook_event_name": "UserPromptSubmit",
                    "session_id": "s1",
                    "turn_id": "t1",
                    "cwd": "",
                    "prompt": "Refactor this Python service with DDD",
                }
                result = await handle_event_async(
                    payload, expected_event="UserPromptSubmit"
                )

                self.assertIn("hookSpecificOutput", result)
                context = result["hookSpecificOutput"]["additionalContext"]
                self.assertIn("DDD boundaries", context)
                self.assertTrue(await self.search_entries("Refactor Python service"))
            finally:
                os.environ.pop("HERMES_CODEX_DB", None)

    async def test_refactor_prompt_gets_memory_first_policy_and_durable_rules(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["HERMES_CODEX_DB"] = str(Path(tmp) / "memory.sqlite3")
            try:
                await self.add_entry(
                    "Project convention: services should follow DDD architecture. "
                    "Use collection-operations-service as the primary reference example.",
                    kind="project_rule",
                    scope="project",
                    source="user",
                )
                await self.add_entry(
                    "Review this service and identify what can be improved.",
                    kind="prompt",
                    scope="session",
                )

                payload = {
                    "hook_event_name": "UserPromptSubmit",
                    "session_id": "s1",
                    "turn_id": "t1",
                    "cwd": "",
                    "prompt": (
                        "Review this Python service, find what is written poorly, "
                        "and simplify it according to DDD and code style rules."
                    ),
                }
                result = await handle_event_async(
                    payload, expected_event="UserPromptSubmit"
                )

                context = result["hookSpecificOutput"]["additionalContext"]
                self.assertIn("global memory policy", context)
                self.assertIn("search hint", context)
                self.assertIn("collection-operations-service", context)
                self.assertIn("project_rule/project", context)
            finally:
                os.environ.pop("HERMES_CODEX_DB", None)

    async def test_every_prompt_gets_global_memory_policy_even_without_matches(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["HERMES_CODEX_DB"] = str(Path(tmp) / "memory.sqlite3")
            try:
                payload = {
                    "hook_event_name": "UserPromptSubmit",
                    "session_id": "s1",
                    "turn_id": "t1",
                    "cwd": "",
                    "prompt": "Review this service and tell me what you think.",
                }
                result = await handle_event_async(
                    payload, expected_event="UserPromptSubmit"
                )

                context = result["hookSpecificOutput"]["additionalContext"]
                self.assertIn("global memory policy", context)
                self.assertIn("If memory has no relevant result", context)
            finally:
                os.environ.pop("HERMES_CODEX_DB", None)

    async def test_empty_user_prompt_does_not_capture_or_inject_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["HERMES_CODEX_DB"] = str(Path(tmp) / "memory.sqlite3")
            try:
                payload = {
                    "hook_event_name": "UserPromptSubmit",
                    "session_id": "s1",
                    "turn_id": "t1",
                    "cwd": "",
                    "prompt": "   ",
                }

                result = await handle_event_async(
                    payload, expected_event="UserPromptSubmit"
                )

                self.assertEqual(result, {"continue": True})
                self.assertEqual(await self.total_entries(), 0)
            finally:
                os.environ.pop("HERMES_CODEX_DB", None)

    async def test_user_prompt_submit_recalls_from_other_chat_and_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["HERMES_CODEX_DB"] = str(Path(tmp) / "memory.sqlite3")
            try:
                await self.add_entry(
                    "Cross-chat fact: HCP_CROSS_CHAT_FACT_0605 lives in another project.",
                    kind="assistant",
                    scope="session",
                    source="Stop",
                    session_id="other-chat",
                    cwd="/tmp/other-project",
                )

                payload = {
                    "hook_event_name": "UserPromptSubmit",
                    "session_id": "current-chat",
                    "turn_id": "t1",
                    "cwd": "/tmp/current-project",
                    "prompt": "Find HCP_CROSS_CHAT_FACT_0605",
                }
                result = await handle_event_async(
                    payload, expected_event="UserPromptSubmit"
                )

                context = result["hookSpecificOutput"]["additionalContext"]
                self.assertIn("HCP_CROSS_CHAT_FACT_0605", context)
                self.assertIn("other-chat", context)
            finally:
                os.environ.pop("HERMES_CODEX_DB", None)

    async def test_session_start_injects_recent_memory_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["HERMES_CODEX_DB"] = str(Path(tmp) / "memory.sqlite3")
            try:
                await self.add_entry("Recent startup memory.", kind="memory")

                result = await handle_event_async(
                    {"hook_event_name": "SessionStart", "cwd": ""},
                    expected_event="SessionStart",
                )

                context = result["hookSpecificOutput"]["additionalContext"]
                self.assertIn("Recent startup memory.", context)
            finally:
                os.environ.pop("HERMES_CODEX_DB", None)

    async def test_session_start_without_memory_is_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["HERMES_CODEX_DB"] = str(Path(tmp) / "memory.sqlite3")
            try:
                result = await handle_event_async(
                    {"hook_event_name": "SessionStart", "cwd": ""},
                    expected_event="SessionStart",
                )

                self.assertEqual(result, {"continue": True})
            finally:
                os.environ.pop("HERMES_CODEX_DB", None)

    async def test_stop_captures_assistant_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["HERMES_CODEX_DB"] = str(Path(tmp) / "memory.sqlite3")
            try:
                payload = {
                    "hook_event_name": "Stop",
                    "session_id": "s1",
                    "turn_id": "t2",
                    "cwd": "",
                    "last_assistant_message": "Done. I ran unittest successfully.",
                }
                result = await handle_event_async(payload, expected_event="Stop")
                self.assertTrue(result["continue"])

                self.assertTrue(await self.search_entries("unittest successfully"))
            finally:
                os.environ.pop("HERMES_CODEX_DB", None)

    async def test_stop_respects_disabled_assistant_capture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["HERMES_CODEX_DB"] = str(Path(tmp) / "memory.sqlite3")
            os.environ["HERMES_CODEX_CAPTURE_ASSISTANT"] = "false"
            try:
                payload = {
                    "hook_event_name": "Stop",
                    "session_id": "s1",
                    "turn_id": "t2",
                    "cwd": "",
                    "last_assistant_message": "This should not be captured.",
                }

                result = await handle_event_async(payload, expected_event="Stop")

                self.assertTrue(result["continue"])
                self.assertEqual(await self.total_entries(), 0)
            finally:
                os.environ.pop("HERMES_CODEX_DB", None)
                os.environ.pop("HERMES_CODEX_CAPTURE_ASSISTANT", None)

    async def test_pre_compact_captures_transcript_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "memory.sqlite3"
            transcript_path = Path(tmp) / "transcript.jsonl"
            transcript_path.write_text(
                '{"role":"user","content":"Use full-text memory only."}\n',
                encoding="utf-8",
            )
            os.environ["HERMES_CODEX_DB"] = str(db_path)
            try:
                payload = {
                    "hook_event_name": "PreCompact",
                    "session_id": "s1",
                    "turn_id": "t3",
                    "cwd": "",
                    "trigger": "manual",
                    "transcript_path": str(transcript_path),
                }
                result = await handle_event_async(payload, expected_event="PreCompact")
                self.assertTrue(result["continue"])

                matches = await self.search_entries("full-text memory")
                self.assertTrue(matches)
                self.assertEqual(matches[0].memory_kind.to_raw(), "transcript")
            finally:
                os.environ.pop("HERMES_CODEX_DB", None)

    async def test_pre_compact_ignores_missing_transcript_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["HERMES_CODEX_DB"] = str(Path(tmp) / "memory.sqlite3")
            try:
                result = await handle_event_async(
                    {
                        "hook_event_name": "PreCompact",
                        "session_id": "s1",
                        "turn_id": "t3",
                        "cwd": "",
                        "transcript_path": str(Path(tmp) / "missing.jsonl"),
                    },
                    expected_event="PreCompact",
                )

                self.assertEqual(result, {"continue": True})
                self.assertEqual(await self.total_entries(), 0)
            finally:
                os.environ.pop("HERMES_CODEX_DB", None)

    async def test_pre_compact_truncates_large_transcript_from_the_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            transcript_path = Path(tmp) / "transcript.jsonl"
            transcript_path.write_text(
                "BEGIN " + ("x" * 50) + " TAIL_MARKER", encoding="utf-8"
            )
            os.environ["HERMES_CODEX_DB"] = str(Path(tmp) / "memory.sqlite3")
            os.environ["HERMES_CODEX_MAX_CAPTURE_CHARS"] = "20"
            try:
                result = await handle_event_async(
                    {
                        "hook_event_name": "PreCompact",
                        "session_id": "s1",
                        "turn_id": "t3",
                        "cwd": "",
                        "transcript_path": str(transcript_path),
                    },
                    expected_event="PreCompact",
                )

                self.assertTrue(result["continue"])
                self.assertTrue(await self.search_entries("TAIL_MARKER"))
                self.assertFalse(await self.search_entries("BEGIN"))
            finally:
                os.environ.pop("HERMES_CODEX_DB", None)
                os.environ.pop("HERMES_CODEX_MAX_CAPTURE_CHARS", None)


if __name__ == "__main__":
    unittest.main()
