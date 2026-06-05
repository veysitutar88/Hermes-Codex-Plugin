<p align="center">
  <img src="assets/logo.svg" alt="Hermes Codex Plugin" width="760">
</p>

<p align="center">
  <a href="plugins/hermes-codex-plugin/LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-10B981.svg"></a>
  <img alt="Python 3.9+" src="https://img.shields.io/badge/python-3.9%2B-3776AB.svg">
  <img alt="Tests: 59 passing" src="https://img.shields.io/badge/tests-59%20passing-10B981.svg">
  <img alt="SQLite FTS5" src="https://img.shields.io/badge/search-SQLite%20FTS5-6366F1.svg">
  <img alt="Embeddings: none" src="https://img.shields.io/badge/embeddings-none-0F172A.svg">
  <img alt="Codex plugin" src="https://img.shields.io/badge/Codex-plugin-22D3EE.svg">
</p>

# Hermes Codex Plugin

Hermes Codex Plugin is a local-first Codex plugin that gives Codex durable memory across chats,
full-text recall, and a lightweight path from repeated rules to reusable skills. It is designed for
developers who want an agent to remember project conventions without sending chat history to a
remote embedding service. Its main benefit is reducing Codex token spend by recalling only the
smallest relevant context instead of replaying whole chats or long prompt blocks.
Before solving a task, the plugin steers Codex to check whether similar work, an existing skill,
or durable user/project rules already exist, so Codex can reuse prior decisions instead of
inventing a fresh approach.

The plugin is intentionally simple:

- local SQLite storage with FTS5 and a `LIKE` fallback;
- Codex lifecycle hooks for capture and recall;
- MCP tools for search, write, delete, stats, and skill drafts;
- Codex-written task summaries through `hermes_codex_remember_summary`;
- memory-first task guidance that applies durable rules during code edits;
- a Python CLI for local inspection and smoke tests;
- DDD-inspired internals with value objects, DTO mappers, commands, and queries.

No embeddings are used. No background daemon is required.

## Why This Exists

Codex is strongest when it has the rules that matter: project architecture decisions, preferred
review style, workflows, and prior choices. Those rules often live in old chats. Hermes Codex Plugin
turns those chats into a local full-text memory layer that can be recalled before the next request
with minimal context and fewer Codex tokens.

Typical use cases:

- remember architecture rules across unrelated Codex sessions;
- search prior chats without manually pasting context back into the prompt;
- keep reusable workflow instructions in local memory;
- save compact task summaries instead of long raw transcript excerpts;
- enforce remembered coding rules, such as keeping imports at the top of a file;
- draft `SKILL.md` files from repeated project rules, including non-English rules when
  Codex judges them to describe a reusable workflow;
- inspect exactly what memory exists, where it came from, and when it was captured.

## Status

| Area | Current state |
| --- | --- |
| Version | `0.10.2` |
| Language | Python 3.9+ |
| Test suite | 59 passing `unittest` tests |
| Storage | SQLite with FTS5, plus `LIKE` fallback |
| Embeddings | None |
| License | MIT |
| Runtime surfaces | Codex hooks, MCP server, CLI |

## Repository Layout

```text
.agents/plugins/marketplace.json        Local Codex marketplace entry
assets/logo.svg                         Open-source logo asset
plugins/hermes-codex-plugin/            Plugin package
plugins/hermes-codex-plugin/hooks/      Codex hook entrypoints
plugins/hermes-codex-plugin/scripts/    MCP wrapper entrypoint
plugins/hermes-codex-plugin/src/        Python source
plugins/hermes-codex-plugin/tests/      Behavioral test suite
```

The plugin package uses these internal layers:

```text
domain/         Entities, value objects, policies, and ports
application/    Commands, queries, DTOs, mappers, and recall services
infrastructure/ SQLite persistence, configuration, logging, filesystem adapters
presentation/   CLI, Codex hook, MCP, and formatting adapters
```

## Install As A Local Codex Plugin

From the repository root:

```bash
codex plugin marketplace add .
codex plugin add hermes-codex-plugin@hermes-codex-plugin
```

Check that Codex sees the plugin:

```bash
codex plugin list --marketplace hermes-codex-plugin
codex mcp get hermes-codex-plugin
```

The MCP server should point at the installed plugin cache and expose the `hermes-codex-plugin`
server.

## Enable Hooks

After installing the plugin, open Codex hooks once and trust the plugin hook definitions. The plugin
uses these Codex lifecycle hooks:

| Hook | What it does |
| --- | --- |
| `SessionStart` | Injects recent local memory when a new session starts. |
| `UserPromptSubmit` | Captures the user prompt and injects relevant memory context. |
| `Stop` | Captures the latest assistant message when enabled. |
| `PreCompact` | Captures a transcript snapshot before context compaction. |

## MCP Tools

The bundled MCP server exposes:

| Tool | Purpose |
| --- | --- |
| `hermes_codex_search` | Search local memory, optionally scoped by cwd. |
| `hermes_codex_search_chats` | Search previous chats across projects. |
| `hermes_codex_remember` | Save a durable, non-secret memory entry. |
| `hermes_codex_remember_summary` | Save a structured Codex-written task summary. |
| `hermes_codex_forget` | Delete a memory entry by id. |
| `hermes_codex_stats` | Show local memory database statistics. |
| `hermes_codex_propose_skill` | Draft a `SKILL.md` from matching memory rules, including multilingual workflow rules. |
| `hermes_codex_write_skill` | Write a reviewed skill file. |

## CLI Usage

Use a temporary database for local testing:

```bash
cd plugins/hermes-codex-plugin
export HERMES_CODEX_DB=/tmp/hermes-codex-plugin.sqlite3
PYTHONPATH=src python3 -m hermes_codex_plugin.presentation.cli.main init
```

Remember a rule:

```bash
PYTHONPATH=src python3 -m hermes_codex_plugin.presentation.cli.main remember \
  "Always run the unit test suite before release." \
  --kind rule \
  --scope project
```

Search memory:

```bash
PYTHONPATH=src python3 -m hermes_codex_plugin.presentation.cli.main search "unit test suite"
```

Show stats:

```bash
PYTHONPATH=src python3 -m hermes_codex_plugin.presentation.cli.main stats
```

Draft a skill from memory:

```bash
PYTHONPATH=src python3 -m hermes_codex_plugin.presentation.cli.main propose-skill \
  --query "release workflow" \
  --name release-workflow
```

## Storage

The memory database path is resolved in this order:

1. `HERMES_CODEX_DB`, when set.
2. `$PLUGIN_DATA/hermes-codex-plugin.sqlite3`, when Codex provides plugin data.
3. An inferred Codex plugin data directory when running from plugin cache.
4. `~/.hermes-codex-plugin/memory.sqlite3` as a fallback.

The schema stores memory entries, metadata JSON, fingerprints for deduplication, and an FTS5
virtual table when available.

## Development

Run the test suite:

```bash
cd plugins/hermes-codex-plugin
PYTHONPATH=src python3 -m unittest discover -s tests
```

Run bytecode compilation checks:

```bash
PYTHONPATH=src python3 -m compileall -q src tests hooks scripts
```

Expected local result:

```text
Ran 52 tests
OK
```

## Privacy And Safety

- Memory is local by default.
- No embedding service is used.
- Obvious API keys, bearer tokens, passwords, and JWT-like values are redacted before storage.
- Redaction is a safety layer, not a complete DLP system.
- Do not intentionally save secrets.

## Design Principles

- Keep the memory backend inspectable.
- Prefer full-text recall before asking users to repeat stable rules.
- Keep domain entities free of primitive fields by using value objects.
- Convert domain entities to DTOs through explicit mapper classes.
- Keep commands and queries in separate packages, one handler per file.
- Do not keep alias or compatibility modules after moving code.
- Keep source artifacts in English.

## Current Limits

- Skill generation is heuristic and should be reviewed before use.
- There is no UI beyond Codex, MCP, hooks, and CLI.
- There is no background daemon.
- Full-text search is lexical, not semantic.

## License

MIT. See [plugins/hermes-codex-plugin/LICENSE](plugins/hermes-codex-plugin/LICENSE).
