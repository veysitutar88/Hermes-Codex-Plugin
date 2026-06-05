import asyncio
import dataclasses
import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Callable, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hermes_codex_plugin import __version__
from hermes_codex_plugin.application.memory.commands.forget_memory import (
    ForgetMemory,
    ForgetMemoryHandler,
)
from hermes_codex_plugin.application.memory.commands.remember_memory import (
    RememberMemory,
    RememberMemoryHandler,
)
from hermes_codex_plugin.application.memory.commands.remember_summary import (
    RememberSummary,
    RememberSummaryHandler,
)
from hermes_codex_plugin.application.memory.mapper import (
    MemoryEntryMapper,
    MemoryStatsMapper,
)
from hermes_codex_plugin.application.memory.queries.get_memory_stats import (
    GetMemoryStatsHandler,
)
from hermes_codex_plugin.application.memory.queries.search_chats import (
    SearchChats,
    SearchChatsHandler,
)
from hermes_codex_plugin.application.memory.queries.search_memory import (
    SearchMemory,
    SearchMemoryHandler,
)
from hermes_codex_plugin.application.skills.mapper import SkillDraftMapper
from hermes_codex_plugin.application.skills.queries.propose_skill import (
    ProposeSkill,
    ProposeSkillHandler,
)
from hermes_codex_plugin.domain.skills.entities import SkillDraft
from hermes_codex_plugin.domain.skills.services import SkillNameNormalizer
from hermes_codex_plugin.infrastructure.config import load_settings
from hermes_codex_plugin.infrastructure.db.connect import open_memory_sessionmaker
from hermes_codex_plugin.infrastructure.db.gateways.memory import (
    MemoryReaderGateway,
    MemoryRepoGateway,
)
from hermes_codex_plugin.infrastructure.skills.filesystem_skill_writer import (
    write_skill,
)
from hermes_codex_plugin.presentation.formatting import format_search_results
from hermes_codex_plugin.presentation.skills.formatting import format_skill_draft

JSONDict = Dict[str, Any]


def main() -> None:
    asyncio.run(async_main())


async def async_main() -> None:
    settings = load_settings()
    async with open_memory_sessionmaker(settings.db_path) as session_maker:
        server = MCPServer(settings, session_maker)
        await server.run()


@asynccontextmanager
async def open_mcp_server():
    settings = load_settings()
    async with open_memory_sessionmaker(settings.db_path) as session_maker:
        yield MCPServer(settings, session_maker)


class MCPServer:
    def __init__(
        self,
        settings,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        self.settings = settings
        self.session_maker = session_maker
        self._skill_mapper = SkillDraftMapper()
        self._skill_name_normalizer = SkillNameNormalizer()
        self.tools: Dict[str, Callable[[JSONDict], Any]] = {
            "hermes_codex_search": self.tool_search,
            "hermes_codex_search_chats": self.tool_search_chats,
            "hermes_codex_remember": self.tool_remember,
            "hermes_codex_remember_summary": self.tool_remember_summary,
            "hermes_codex_forget": self.tool_forget,
            "hermes_codex_stats": self.tool_stats,
            "hermes_codex_propose_skill": self.tool_propose_skill,
            "hermes_codex_write_skill": self.tool_write_skill,
        }

    async def run(self) -> None:
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                message = json.loads(line)
                response = await self.handle_message(message)
            except Exception as exc:
                response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32603, "message": str(exc)},
                }
            if response is not None:
                sys.stdout.write(json.dumps(response, ensure_ascii=True) + "\n")
                sys.stdout.flush()

    async def handle_message(self, message: JSONDict) -> Any:
        method = message.get("method")
        request_id = message.get("id")
        if request_id is None:
            return None
        if method == "initialize":
            return self.response(
                request_id,
                {
                    "protocolVersion": message.get("params", {}).get(
                        "protocolVersion", "2024-11-05"
                    ),
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "hermes-codex-plugin",
                        "version": __version__,
                    },
                    "instructions": (
                        "Use hermes_codex_search_chats before relying on missing "
                        "cross-chat context. Use hermes_codex_search for narrower "
                        "local memory search. "
                        "Use hermes_codex_remember only for durable, non-secret facts. "
                        "After substantial tasks, write a concise task summary and save "
                        "it with hermes_codex_remember_summary instead of storing raw "
                        "chat transcripts. "
                        "Use semantic judgment across languages to decide whether "
                        "repeated workflow rules should become skill drafts. "
                        "Skill drafts are proposals and should be reviewed before writing."
                    ),
                },
            )
        if method == "tools/list":
            return self.response(request_id, {"tools": tool_schemas()})
        if method == "tools/call":
            params = message.get("params") or {}
            tool_name = params.get("name")
            args = params.get("arguments") or {}
            if tool_name not in self.tools:
                return self.error(
                    request_id, -32601, "Unknown tool {}".format(tool_name)
                )
            result = await self.tools[tool_name](args)
            return self.response(request_id, text_result(result))
        return self.error(request_id, -32601, "Unknown method {}".format(method))

    @staticmethod
    def response(request_id: Any, result: Any) -> JSONDict:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    @staticmethod
    def error(request_id: Any, code: int, message: str) -> JSONDict:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }

    async def tool_search(self, args: JSONDict) -> str:
        query = str(args.get("query") or "")
        limit = int(args.get("limit") or self.settings.recall_limit)
        cwd = args.get("cwd")
        async with self.session_maker() as session:
            memory_reader = MemoryReaderGateway(session, self.settings.db_path)
            results = await SearchMemoryHandler(memory_reader, MemoryEntryMapper())(
                SearchMemory(query, limit=limit, cwd=str(cwd) if cwd else None)
            )
        return format_search_results(results)

    async def tool_search_chats(self, args: JSONDict) -> str:
        query = str(args.get("query") or "")
        limit = int(args.get("limit") or self.settings.recall_limit)
        async with self.session_maker() as session:
            memory_reader = MemoryReaderGateway(session, self.settings.db_path)
            results = await SearchChatsHandler(memory_reader, MemoryEntryMapper())(
                SearchChats(query, limit=limit)
            )
        return format_search_results(results)

    async def tool_remember(self, args: JSONDict) -> str:
        content = str(args.get("content") or "").strip()
        if not content:
            raise ValueError("content is required")
        async with self.session_maker() as session:
            memory_repo = MemoryRepoGateway(session, self.settings.db_path)
            entry_id = await RememberMemoryHandler(memory_repo, session)(
                RememberMemory(
                    content,
                    kind=str(args.get("kind") or "memory"),
                    scope=str(args.get("scope") or "global"),
                    source=str(args.get("source") or "mcp"),
                    cwd=str(args.get("cwd") or ""),
                    metadata={"tags": args.get("tags") or []},
                )
            )
        return "Remembered entry #{}".format(entry_id)

    async def tool_remember_summary(self, args: JSONDict) -> str:
        goal = str(args.get("goal") or "").strip()
        if not goal:
            raise ValueError("goal is required")
        async with self.session_maker() as session:
            memory_repo = MemoryRepoGateway(session, self.settings.db_path)
            entry_id = await RememberSummaryHandler(memory_repo, session)(
                RememberSummary(
                    goal=goal,
                    outcome=str(args.get("outcome") or ""),
                    decisions=self._string_list(args.get("decisions")),
                    rules_learned=self._string_list(args.get("rules_learned")),
                    files_touched=self._string_list(args.get("files_touched")),
                    open_questions=self._string_list(args.get("open_questions")),
                    keywords=self._string_list(args.get("keywords")),
                    cwd=str(args.get("cwd") or ""),
                    session_id=str(args.get("session_id") or ""),
                    turn_id=str(args.get("turn_id") or ""),
                    tags=self._string_list(args.get("tags")),
                )
            )
        return "Remembered summary #{}".format(entry_id)

    async def tool_forget(self, args: JSONDict) -> str:
        raw_id = args.get("id")
        if raw_id is None:
            raise ValueError("id is required")
        entry_id = int(raw_id)
        async with self.session_maker() as session:
            memory_repo = MemoryRepoGateway(session, self.settings.db_path)
            deleted = await ForgetMemoryHandler(memory_repo, session)(
                ForgetMemory(entry_id)
            )
        return "Deleted entry #{}".format(entry_id) if deleted else "Entry not found"

    async def tool_stats(self, args: JSONDict) -> str:
        del args
        async with self.session_maker() as session:
            memory_reader = MemoryReaderGateway(session, self.settings.db_path)
            stats = await GetMemoryStatsHandler(memory_reader, MemoryStatsMapper())()
        return json.dumps(dataclasses.asdict(stats), indent=2, sort_keys=True)

    async def tool_propose_skill(self, args: JSONDict) -> str:
        async with self.session_maker() as session:
            memory_reader = MemoryReaderGateway(session, self.settings.db_path)
            draft = await ProposeSkillHandler(memory_reader)(
                ProposeSkill(
                    query=str(args.get("query") or ""),
                    name=str(args.get("name") or "learned-workflow"),
                    description=args.get("description"),
                    limit=int(args.get("limit") or 25),
                )
            )
        return format_skill_draft(self._skill_mapper.to_dto(draft))

    async def tool_write_skill(self, args: JSONDict) -> str:
        name = self._skill_name_normalizer.normalize(
            str(args.get("name") or "learned-workflow")
        )
        description = str(
            args.get("description")
            or "Use when Codex should apply learned workflow rules."
        )
        rules = args.get("rules") or []
        if not isinstance(rules, list) or not all(
            isinstance(rule, str) for rule in rules
        ):
            raise ValueError("rules must be a list of strings")
        if not rules:
            raise ValueError("rules must not be empty")
        skills_root = args.get("skills_root")
        draft = SkillDraft.from_raw(name=name, description=description, rules=rules)
        draft_dto = self._skill_mapper.to_dto(draft)
        path = write_skill(
            draft_dto,
            format_skill_draft(draft_dto),
            skills_root=Path(skills_root).expanduser() if skills_root else None,
            overwrite=bool(args.get("overwrite")),
        )
        return "Wrote skill to {}".format(path)

    @staticmethod
    def _string_list(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        text = str(value).strip()
        return [text] if text else []


def text_result(value: Any) -> JSONDict:
    return {
        "content": [
            {
                "type": "text",
                "text": str(value),
            }
        ],
        "isError": False,
    }


def tool_schemas() -> List[JSONDict]:
    return [
        {
            "name": "hermes_codex_search",
            "description": "Search local Codex memory with full-text search.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                    "cwd": {"type": "string"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "hermes_codex_search_chats",
            "description": (
                "Search across previous Codex chats/sessions in the local full-text memory "
                "database, regardless of the current project directory."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        },
        {
            "name": "hermes_codex_remember",
            "description": "Save a durable, non-secret memory entry.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "kind": {"type": "string", "default": "memory"},
                    "scope": {"type": "string", "default": "global"},
                    "source": {"type": "string", "default": "mcp"},
                    "cwd": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["content"],
            },
        },
        {
            "name": "hermes_codex_remember_summary",
            "description": (
                "Save a concise Codex-written task summary as searchable memory. "
                "Use this after substantial tasks instead of storing raw chat text."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "goal": {"type": "string"},
                    "outcome": {"type": "string"},
                    "decisions": {"type": "array", "items": {"type": "string"}},
                    "rules_learned": {"type": "array", "items": {"type": "string"}},
                    "files_touched": {"type": "array", "items": {"type": "string"}},
                    "open_questions": {"type": "array", "items": {"type": "string"}},
                    "keywords": {"type": "array", "items": {"type": "string"}},
                    "cwd": {"type": "string"},
                    "session_id": {"type": "string"},
                    "turn_id": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["goal"],
            },
        },
        {
            "name": "hermes_codex_forget",
            "description": "Delete a memory entry by id.",
            "inputSchema": {
                "type": "object",
                "properties": {"id": {"type": "integer"}},
                "required": ["id"],
            },
        },
        {
            "name": "hermes_codex_stats",
            "description": "Show local memory storage statistics.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "hermes_codex_propose_skill",
            "description": (
                "Draft a SKILL.md from matching or recent memory rules, including "
                "multilingual rules selected by Codex semantic judgment."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "name": {"type": "string", "default": "learned-workflow"},
                    "description": {"type": "string"},
                    "limit": {"type": "integer", "default": 25},
                },
            },
        },
        {
            "name": "hermes_codex_write_skill",
            "description": "Write a reviewed skill to ~/.agents/skills or a provided skills root.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "rules": {"type": "array", "items": {"type": "string"}},
                    "skills_root": {"type": "string"},
                    "overwrite": {"type": "boolean", "default": False},
                },
                "required": ["name", "description", "rules"],
            },
        },
    ]
