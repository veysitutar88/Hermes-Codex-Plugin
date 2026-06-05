import tempfile
import unittest
from pathlib import Path

from hermes_codex_plugin.application.skills.mapper import SkillDraftMapper
from hermes_codex_plugin.application.skills.queries.propose_skill import (
    ProposeSkill,
    ProposeSkillHandler,
)
from hermes_codex_plugin.infrastructure.db.connect import open_memory_session
from hermes_codex_plugin.infrastructure.db.gateways.memory import (
    MemoryReaderGateway,
    MemoryRepoGateway,
)
from hermes_codex_plugin.infrastructure.skills.filesystem_skill_writer import (
    write_skill,
)
from hermes_codex_plugin.presentation.skills.formatting import format_skill_draft


class SkillMinerTest(unittest.IsolatedAsyncioTestCase):
    async def test_propose_skill_extracts_rule_sentences(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "memory.sqlite3"
            async with open_memory_session(db_path) as session:
                repo = MemoryRepoGateway(session, db_path)
                reader = MemoryReaderGateway(session, db_path)
                await repo.add_entry(
                    "Always run pytest before opening a PR.", kind="rule"
                )
                await repo.add_entry(
                    "Prefer small patches and focused tests.", kind="rule"
                )

                draft = await ProposeSkillHandler(reader)(
                    ProposeSkill(query="pytest patches", name="review-flow")
                )
                markdown = format_skill_draft(SkillDraftMapper().to_dto(draft))

                self.assertIn("name: review-flow", markdown)
                self.assertIn("Always run pytest", markdown)
                self.assertIn("Prefer small patches", markdown)

    async def test_propose_skill_uses_fallback_rule_when_no_rule_sentences_match(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "memory.sqlite3"
            async with open_memory_session(db_path) as session:
                repo = MemoryRepoGateway(session, db_path)
                reader = MemoryReaderGateway(session, db_path)
                await repo.add_entry(
                    "This is just a neutral observation.", kind="memory"
                )

                draft = await ProposeSkillHandler(reader)(
                    ProposeSkill(query="neutral", name="neutral-flow")
                )

                self.assertIn(
                    "Review local memory before repeating this workflow.",
                    format_skill_draft(SkillDraftMapper().to_dto(draft)),
                )

    async def test_write_skill_respects_overwrite_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "memory.sqlite3"
            async with open_memory_session(db_path) as session:
                repo = MemoryRepoGateway(session, db_path)
                reader = MemoryReaderGateway(session, db_path)
                await repo.add_entry(
                    "Always run pytest before opening a PR.", kind="rule"
                )
                draft = await ProposeSkillHandler(reader)(
                    ProposeSkill(query="pytest", name="review-flow")
                )
            draft_dto = SkillDraftMapper().to_dto(draft)
            markdown = format_skill_draft(draft_dto)
            skills_root = Path(tmp) / "skills"

            skill_path = write_skill(draft_dto, markdown, skills_root=skills_root)

            self.assertTrue(skill_path.exists())
            with self.assertRaises(FileExistsError):
                write_skill(draft_dto, markdown, skills_root=skills_root)

            overwritten_path = write_skill(
                draft_dto,
                markdown,
                skills_root=skills_root,
                overwrite=True,
            )
            self.assertEqual(overwritten_path, skill_path)


if __name__ == "__main__":
    unittest.main()
