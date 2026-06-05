import argparse
import asyncio
import dataclasses
import json
import sys
from pathlib import Path
from typing import Optional

from hermes_codex_plugin.application.memory.commands.forget_memory import (
    ForgetMemory,
    ForgetMemoryHandler,
)
from hermes_codex_plugin.application.memory.commands.remember_memory import (
    RememberMemory,
    RememberMemoryHandler,
)
from hermes_codex_plugin.application.memory.mapper import (
    MemoryEntryMapper,
    MemoryStatsMapper,
)
from hermes_codex_plugin.application.memory.queries.get_memory_stats import (
    GetMemoryStatsHandler,
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
from hermes_codex_plugin.infrastructure.config import load_settings
from hermes_codex_plugin.infrastructure.db.connect import open_memory_session
from hermes_codex_plugin.infrastructure.db.gateways.memory import (
    MemoryReaderGateway,
    MemoryRepoGateway,
)
from hermes_codex_plugin.infrastructure.skills.filesystem_skill_writer import (
    write_skill,
)
from hermes_codex_plugin.presentation.formatting import format_search_results
from hermes_codex_plugin.presentation.hooks.controller import handle_event_async
from hermes_codex_plugin.presentation.skills.formatting import format_skill_draft


def write_stdout(message: str) -> None:
    sys.stdout.write(message)
    if not message.endswith("\n"):
        sys.stdout.write("\n")


def main(argv: Optional[list] = None) -> None:
    asyncio.run(async_main(argv))


async def async_main(argv: Optional[list] = None) -> None:
    parser = argparse.ArgumentParser(prog="hermes-codex-plugin")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init")

    remember = sub.add_parser("remember")
    remember.add_argument("content")
    remember.add_argument("--kind", default="memory")
    remember.add_argument("--scope", default="global")
    remember.add_argument("--source", default="cli")
    remember.add_argument("--cwd", default="")

    search = sub.add_parser("search")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=5)

    forget = sub.add_parser("forget")
    forget.add_argument("id", type=int)

    sub.add_parser("stats")

    propose = sub.add_parser("propose-skill")
    propose.add_argument("--query", default="")
    propose.add_argument("--name", default="learned-workflow")
    propose.add_argument("--description")
    propose.add_argument("--write", action="store_true")
    propose.add_argument("--overwrite", action="store_true")
    propose.add_argument("--skills-root")

    hook = sub.add_parser("hook")
    hook.add_argument("event")
    hook.add_argument("payload", help="JSON hook payload")

    args = parser.parse_args(argv)
    settings = load_settings()
    memory_mapper = MemoryEntryMapper()
    stats_mapper = MemoryStatsMapper()
    skill_mapper = SkillDraftMapper()

    if args.command == "hook":
        payload = json.loads(args.payload)
        write_stdout(
            json.dumps(
                await handle_event_async(payload, expected_event=args.event),
                indent=2,
            )
        )
        return

    async with open_memory_session(settings.db_path) as session:
        memory_reader = MemoryReaderGateway(session, settings.db_path)
        memory_repo = MemoryRepoGateway(session, settings.db_path)

        if args.command == "init":
            stats = await GetMemoryStatsHandler(memory_reader, stats_mapper)()
            write_stdout(
                json.dumps(dataclasses.asdict(stats), indent=2, sort_keys=True)
            )
        elif args.command == "remember":
            entry_id = await RememberMemoryHandler(memory_repo, session)(
                RememberMemory(
                    args.content,
                    kind=args.kind,
                    scope=args.scope,
                    source=args.source,
                    cwd=args.cwd,
                )
            )
            write_stdout("remembered #{}".format(entry_id))
        elif args.command == "search":
            results = await SearchMemoryHandler(memory_reader, memory_mapper)(
                SearchMemory(args.query, limit=args.limit)
            )
            write_stdout(format_search_results(results))
        elif args.command == "forget":
            deleted = await ForgetMemoryHandler(memory_repo, session)(
                ForgetMemory(args.id)
            )
            write_stdout("deleted" if deleted else "not found")
        elif args.command == "stats":
            stats = await GetMemoryStatsHandler(memory_reader, stats_mapper)()
            write_stdout(
                json.dumps(dataclasses.asdict(stats), indent=2, sort_keys=True)
            )
        elif args.command == "propose-skill":
            draft = await ProposeSkillHandler(memory_reader)(
                ProposeSkill(
                    query=args.query,
                    name=args.name,
                    description=args.description,
                )
            )
            if args.write:
                root = Path(args.skills_root).expanduser() if args.skills_root else None
                draft_dto = skill_mapper.to_dto(draft)
                path = write_skill(
                    draft_dto,
                    format_skill_draft(draft_dto),
                    skills_root=root,
                    overwrite=args.overwrite,
                )
                write_stdout(str(path))
            else:
                write_stdout(format_skill_draft(skill_mapper.to_dto(draft)))


if __name__ == "__main__":
    main()
