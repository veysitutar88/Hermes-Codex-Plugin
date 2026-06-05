from dataclasses import dataclass, field
from typing import Dict, List, Optional

from hermes_codex_plugin.application.common.interfaces import UnitOfWork
from hermes_codex_plugin.application.memory.interfaces import MemoryRepo


@dataclass(frozen=True)
class RememberSummary:
    goal: str
    outcome: str = ""
    decisions: List[str] = field(default_factory=list)
    rules_learned: List[str] = field(default_factory=list)
    files_touched: List[str] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    cwd: str = ""
    session_id: str = ""
    turn_id: str = ""
    source: str = "mcp-summary"
    tags: List[str] = field(default_factory=list)


class SummaryContentFormatter:
    def format(self, summary: RememberSummary) -> str:
        sections = [
            self._line("Goal", summary.goal),
            self._line("Outcome", summary.outcome),
            self._list("Decisions", summary.decisions),
            self._list("Rules learned", summary.rules_learned),
            self._list("Files touched", summary.files_touched),
            self._list("Open questions", summary.open_questions),
            self._line(
                "Search keywords", ", ".join(self._clean_items(summary.keywords))
            ),
        ]
        return "\n".join(section for section in sections if section).strip()

    def _line(self, heading: str, value: str) -> str:
        clean = " ".join(str(value or "").split())
        if not clean:
            return ""
        return "{}: {}".format(heading, clean)

    def _list(self, heading: str, values: List[str]) -> str:
        clean_values = self._clean_items(values)
        if not clean_values:
            return ""
        return "{}:\n{}".format(
            heading,
            "\n".join("- {}".format(value) for value in clean_values),
        )

    def _clean_items(self, values: List[str]) -> List[str]:
        clean_values = []
        for value in values:
            clean = " ".join(str(value or "").split())
            if clean:
                clean_values.append(clean)
        return clean_values


class RememberSummaryHandler:
    def __init__(
        self,
        memory_repo: MemoryRepo,
        uow: UnitOfWork,
        formatter: Optional[SummaryContentFormatter] = None,
    ) -> None:
        self._memory_repo = memory_repo
        self._uow = uow
        self._formatter = formatter or SummaryContentFormatter()

    async def __call__(self, command: RememberSummary) -> int:
        content = self._formatter.format(command)
        entry_id = await self._memory_repo.add_entry(
            content,
            kind="summary",
            scope="session",
            source=command.source,
            session_id=command.session_id,
            turn_id=command.turn_id,
            cwd=command.cwd,
            metadata=self._metadata(command),
        )
        await self._uow.commit()
        return entry_id

    def _metadata(self, command: RememberSummary) -> Dict[str, object]:
        return {
            "summary": True,
            "tags": list(command.tags),
            "keywords": list(command.keywords),
        }
