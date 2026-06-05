from dataclasses import dataclass
from typing import Optional

from hermes_codex_plugin.application.memory.interfaces import MemoryReader
from hermes_codex_plugin.domain.skills.entities import SkillDraft
from hermes_codex_plugin.domain.skills.services import (
    SkillNameNormalizer,
    SkillRuleExtractor,
)


@dataclass(frozen=True)
class ProposeSkill:
    query: str = ""
    name: str = "learned-workflow"
    description: Optional[str] = None
    limit: int = 25


class ProposeSkillHandler:
    def __init__(
        self,
        memory_reader: MemoryReader,
        rule_extractor: Optional[SkillRuleExtractor] = None,
        name_normalizer: Optional[SkillNameNormalizer] = None,
    ) -> None:
        self._memory_reader = memory_reader
        self._rule_extractor = rule_extractor or SkillRuleExtractor()
        self._name_normalizer = name_normalizer or SkillNameNormalizer()

    async def __call__(self, query: ProposeSkill) -> SkillDraft:
        entries = (
            await self._memory_reader.search(query.query, limit=query.limit)
            if query.query
            else await self._memory_reader.recent(limit=query.limit)
        )
        rules = self._rule_extractor.extract(entries)
        if not rules:
            rules = ["Review local memory before repeating this workflow."]
        description = query.description
        if description is None:
            description = (
                "Use when Codex should apply learned local workflow rules related to {}."
            ).format(query.query or "recent work")
        return SkillDraft.from_raw(
            name=self._name_normalizer.normalize(query.name),
            description=description,
            rules=rules[:12],
        )
