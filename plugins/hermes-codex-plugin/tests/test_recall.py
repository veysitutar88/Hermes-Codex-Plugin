import tempfile
import unittest
from pathlib import Path

from hermes_codex_plugin.application.memory.recall import MemoryRecallService
from hermes_codex_plugin.infrastructure.db.connect import open_memory_session
from hermes_codex_plugin.infrastructure.db.gateways.memory import (
    MemoryReaderGateway,
    MemoryRepoGateway,
)


class MemoryRecallServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_recall_includes_same_cwd_global_and_cross_chat_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "memory.sqlite3"
            async with open_memory_session(db_path) as session:
                repo = MemoryRepoGateway(session, db_path)
                reader = MemoryReaderGateway(session, db_path)
                same_cwd_id = await repo.add_entry(
                    "Rule: HCP_RECALL_SAME_CWD should be used.",
                    kind="rule",
                    cwd="/tmp/current",
                )
                global_id = await repo.add_entry(
                    "Memory: HCP_RECALL_GLOBAL should be used.",
                    kind="memory",
                )
                cross_chat_id = await repo.add_entry(
                    "Assistant note: HCP_RECALL_CROSS_CHAT should be used.",
                    kind="assistant",
                    session_id="old-chat",
                    cwd="/tmp/other",
                )
                summary_id = await repo.add_entry(
                    "Summary: HCP_RECALL_SUMMARY captures prior implementation decisions.",
                    kind="summary",
                    cwd="/tmp/current",
                )

                results = await MemoryRecallService(reader).recall(
                    (
                        "HCP_RECALL_SAME_CWD HCP_RECALL_GLOBAL "
                        "HCP_RECALL_CROSS_CHAT HCP_RECALL_SUMMARY"
                    ),
                    limit=10,
                    cwd="/tmp/current",
                )

                self.assertEqual(
                    {entry.entry_id.to_raw() for entry in results},
                    {same_cwd_id, global_id, cross_chat_id, summary_id},
                )

    async def test_recent_durable_ignores_transient_prompt_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "memory.sqlite3"
            async with open_memory_session(db_path) as session:
                repo = MemoryRepoGateway(session, db_path)
                reader = MemoryReaderGateway(session, db_path)
                prompt_id = await repo.add_entry(
                    "Prompt history should not be standing memory.",
                    kind="prompt",
                )
                rule_id = await repo.add_entry(
                    "Always keep durable rules.",
                    kind="user_rule",
                )

                results = await MemoryRecallService(reader).recent_durable(limit=5)
                ids = [entry.entry_id.to_raw() for entry in results]

                self.assertIn(rule_id, ids)
                self.assertNotIn(prompt_id, ids)

    async def test_recall_deduplicates_entries_found_by_multiple_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "memory.sqlite3"
            async with open_memory_session(db_path) as session:
                repo = MemoryRepoGateway(session, db_path)
                reader = MemoryReaderGateway(session, db_path)
                entry_id = await repo.add_entry(
                    "Rule: HCP_DEDUPE should only appear once.",
                    kind="rule",
                    cwd="/tmp/current",
                )

                results = await MemoryRecallService(reader).recall(
                    "HCP_DEDUPE",
                    limit=10,
                    cwd="/tmp/current",
                )

                ids = [entry.entry_id.to_raw() for entry in results]

                self.assertEqual(ids.count(entry_id), 1)


if __name__ == "__main__":
    unittest.main()
