import unittest

from hermes_codex_plugin.domain.memory.entities import MemoryEntry
from hermes_codex_plugin.domain.memory.value_objects import (
    MemoryContent,
    MemoryCreatedAt,
    MemoryCwd,
    MemoryEntryId,
    MemoryKind,
    MemoryMetadata,
    MemoryScope,
    MemorySessionId,
    MemorySource,
    MemoryTurnId,
)


class MemoryDomainTest(unittest.TestCase):
    def test_memory_entry_uses_value_object_fields(self) -> None:
        entry = MemoryEntry.from_raw(
            id=1,
            kind="rule",
            scope="project",
            source="test",
            session_id="s1",
            turn_id="t1",
            cwd="/tmp/project",
            content="Always run tests.",
            metadata={"tag": "qa"},
            created_at="2026-06-05T12:00:00Z",
        )

        self.assertEqual(entry.entry_id, MemoryEntryId(1))
        self.assertEqual(entry.memory_kind, MemoryKind("rule"))
        self.assertEqual(entry.memory_scope, MemoryScope("project"))
        self.assertEqual(entry.memory_source, MemorySource("test"))
        self.assertEqual(entry.session, MemorySessionId("s1"))
        self.assertEqual(entry.turn, MemoryTurnId("t1"))
        self.assertEqual(entry.current_working_directory, MemoryCwd("/tmp/project"))
        self.assertEqual(entry.body, MemoryContent("Always run tests."))
        self.assertEqual(entry.meta, MemoryMetadata({"tag": "qa"}))
        self.assertEqual(entry.created_time, MemoryCreatedAt("2026-06-05T12:00:00Z"))

    def test_memory_entry_redacts_content_when_created(self) -> None:
        entry = MemoryEntry.from_raw(
            id=1,
            kind="memory",
            scope="global",
            source="test",
            session_id="",
            turn_id="",
            cwd="",
            content="token=super-secret-value",
            metadata={},
            created_at="2026-06-05T12:00:00Z",
        )

        self.assertEqual(entry.body, MemoryContent("[REDACTED]"))

    def test_memory_value_objects_validate_required_values(self) -> None:
        invalid_cases = [
            (MemoryEntryId, 0),
            (MemoryKind, ""),
            (MemoryScope, " "),
            (MemoryContent, ""),
            (MemoryMetadata, []),
        ]

        for value_object, value in invalid_cases:
            with self.subTest(value_object=value_object.__name__):
                with self.assertRaises(ValueError):
                    value_object(value)


if __name__ == "__main__":
    unittest.main()
