import tempfile
import unittest
from pathlib import Path

from hermes_codex_plugin.infrastructure.db.connect import open_memory_session
from hermes_codex_plugin.infrastructure.db.gateways.memory import (
    MemoryReaderGateway,
    MemoryRepoGateway,
)


class MemoryStorageGatewayTest(unittest.IsolatedAsyncioTestCase):
    async def test_add_and_search_with_full_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "memory.sqlite3"
            async with open_memory_session(db_path) as session:
                repo = MemoryRepoGateway(session, db_path)
                reader = MemoryReaderGateway(session, db_path)
                entry_id = await repo.add_entry(
                    "Always run unit tests before shipping Python changes.",
                    kind="rule",
                    scope="project",
                )

                results = await reader.search("unit tests python", limit=5)

                self.assertEqual(results[0].entry_id.to_raw(), entry_id)
                self.assertIn("unit tests", results[0].body.to_raw())
                self.assertEqual((await reader.stats())["total_entries"], 1)

    async def test_delete_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "memory.sqlite3"
            async with open_memory_session(db_path) as session:
                repo = MemoryRepoGateway(session, db_path)
                reader = MemoryReaderGateway(session, db_path)
                entry_id = await repo.add_entry("Remember this temporary fact.")

                self.assertTrue(await repo.delete_entry(entry_id))
                self.assertFalse(await reader.search("temporary fact"))

    async def test_search_can_filter_kinds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "memory.sqlite3"
            async with open_memory_session(db_path) as session:
                repo = MemoryRepoGateway(session, db_path)
                reader = MemoryReaderGateway(session, db_path)
                rule_id = await repo.add_entry(
                    "Project convention: use DDD.",
                    kind="project_rule",
                )
                await repo.add_entry("User asked about DDD.", kind="prompt")

                results = await reader.search("DDD", kinds=["project_rule"])

                self.assertEqual(
                    [entry.entry_id.to_raw() for entry in results], [rule_id]
                )

    async def test_duplicate_entry_returns_existing_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "memory.sqlite3"
            async with open_memory_session(db_path) as session:
                repo = MemoryRepoGateway(session, db_path)
                reader = MemoryReaderGateway(session, db_path)

                first_id = await repo.add_entry("Remember this once.", kind="memory")
                second_id = await repo.add_entry("Remember this once.", kind="memory")

                self.assertEqual(first_id, second_id)
                self.assertEqual((await reader.stats())["total_entries"], 1)

    async def test_redacts_obvious_secrets_before_storage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "memory.sqlite3"
            async with open_memory_session(db_path) as session:
                repo = MemoryRepoGateway(session, db_path)
                reader = MemoryReaderGateway(session, db_path)

                await repo.add_entry("token=super-secret-value", kind="memory")
                results = await reader.search("REDACTED")

                self.assertEqual(results[0].body.to_raw(), "[REDACTED]")
                self.assertFalse(await reader.search("super-secret-value"))

    async def test_empty_content_and_empty_query_are_ignored_safely(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "memory.sqlite3"
            async with open_memory_session(db_path) as session:
                repo = MemoryRepoGateway(session, db_path)
                reader = MemoryReaderGateway(session, db_path)

                with self.assertRaises(ValueError):
                    await repo.add_entry("   ")

                self.assertEqual(await reader.search("   "), [])

    async def test_search_can_exclude_kinds_and_filter_by_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "memory.sqlite3"
            async with open_memory_session(db_path) as session:
                repo = MemoryRepoGateway(session, db_path)
                reader = MemoryReaderGateway(session, db_path)
                same_cwd_id = await repo.add_entry(
                    "HCP_CWD_FILTER same project.",
                    kind="memory",
                    cwd="/tmp/current",
                )
                global_id = await repo.add_entry(
                    "HCP_CWD_FILTER global memory.",
                    kind="rule",
                    cwd="",
                )
                await repo.add_entry(
                    "HCP_CWD_FILTER other project.",
                    kind="memory",
                    cwd="/tmp/other",
                )

                results = await reader.search(
                    "HCP_CWD_FILTER",
                    cwd="/tmp/current",
                    exclude_kinds=["rule"],
                )

                ids = [entry.entry_id.to_raw() for entry in results]

                self.assertEqual(ids, [same_cwd_id])
                self.assertNotIn(global_id, ids)

    async def test_like_search_fallback_finds_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "memory.sqlite3"
            async with open_memory_session(db_path) as session:
                repo = MemoryRepoGateway(session, db_path)
                reader = MemoryReaderGateway(session, db_path)
                entry_id = await repo.add_entry(
                    "HCP_LIKE_FALLBACK works.", kind="memory"
                )

                async def no_fts() -> bool:
                    return False

                reader.has_fts = no_fts

                results = await reader.search("HCP_LIKE_FALLBACK")

                self.assertEqual(
                    [entry.entry_id.to_raw() for entry in results], [entry_id]
                )

    async def test_delete_missing_entry_returns_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "memory.sqlite3"
            async with open_memory_session(db_path) as session:
                repo = MemoryRepoGateway(session, db_path)

                self.assertFalse(await repo.delete_entry(999))

    async def test_search_is_only_exposed_by_reader(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "memory.sqlite3"
            async with open_memory_session(db_path) as session:
                repo = MemoryRepoGateway(session, db_path)
                reader = MemoryReaderGateway(session, db_path)

                self.assertFalse(hasattr(repo, "search"))
                self.assertTrue(hasattr(reader, "search"))


if __name__ == "__main__":
    unittest.main()
