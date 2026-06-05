<p align="center">
  <img src="../../assets/logo.svg" alt="Hermes Codex Plugin" width="720">
</p>

<p align="center">
  <img alt="Python 3.9+" src="https://img.shields.io/badge/python-3.9%2B-3776AB.svg">
  <img alt="Tests: 59 passing" src="https://img.shields.io/badge/tests-59%20passing-10B981.svg">
  <img alt="SQLite FTS5" src="https://img.shields.io/badge/search-SQLite%20FTS5-6366F1.svg">
  <img alt="Embeddings: none" src="https://img.shields.io/badge/embeddings-none-0F172A.svg">
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-10B981.svg">
</p>

# Hermes Codex Plugin

Hermes Codex Plugin is a local-first memory and skill evolution plugin for Codex. It captures
useful conversation context through Codex hooks, recalls relevant memory with SQLite full-text
search, exposes MCP tools for direct memory operations, and drafts reusable `SKILL.md` files from
repeated rules. The main benefit is reducing Codex token spend by injecting only the smallest
relevant context instead of replaying whole chats or long prompt blocks.
Before solving a task, it nudges Codex to check memory for similar work, existing skills, and
durable user/project rules so remembered constraints guide the implementation.

## Features

- Local SQLite memory with FTS5 and `LIKE` fallback.
- Cross-chat memory search through MCP.
- Minimal relevant recall to reduce Codex token spend.
- Memory-first task guidance for similar work, skills, and durable coding rules.
- Structured task summaries saved by Codex through MCP.
- Prompt, assistant response, and transcript capture through hooks.
- Durable memory entries for user rules and project conventions.
- Skill draft generation from repeated workflow rules, including multilingual rules when Codex judges they should become reusable workflow guidance.
- CLI for local inspection and smoke tests.
- DDD-inspired Python package structure.

## Install From The Repository Root

```bash
codex plugin marketplace add .
codex plugin add hermes-codex-plugin@hermes-codex-plugin
```

Verify installation:

```bash
codex plugin list --marketplace hermes-codex-plugin
codex mcp get hermes-codex-plugin
```

## Local CLI

```bash
export HERMES_CODEX_DB=/tmp/hermes-codex-plugin.sqlite3
PYTHONPATH=src python3 -m hermes_codex_plugin.presentation.cli.main init
PYTHONPATH=src python3 -m hermes_codex_plugin.presentation.cli.main remember "Always run tests." --kind rule
PYTHONPATH=src python3 -m hermes_codex_plugin.presentation.cli.main search "run tests"
PYTHONPATH=src python3 -m hermes_codex_plugin.presentation.cli.main stats
```

## MCP Tools

| Tool | Purpose |
| --- | --- |
| `hermes_codex_search` | Search local memory, optionally scoped by cwd. |
| `hermes_codex_search_chats` | Search previous chats across projects. |
| `hermes_codex_remember` | Save durable non-secret memory. |
| `hermes_codex_remember_summary` | Save a structured Codex-written task summary. |
| `hermes_codex_forget` | Delete a memory entry by id. |
| `hermes_codex_stats` | Show database statistics. |
| `hermes_codex_propose_skill` | Draft a skill from memory rules, including multilingual workflow rules. |
| `hermes_codex_write_skill` | Write a reviewed skill to disk. |

## Hooks

| Hook | Behavior |
| --- | --- |
| `SessionStart` | Injects recent local memory. |
| `UserPromptSubmit` | Captures the prompt and injects relevant recall context. |
| `Stop` | Captures the latest assistant response when enabled. |
| `PreCompact` | Captures a transcript snapshot before context compaction. |

## Storage Resolution

The database path is selected in this order:

1. `HERMES_CODEX_DB`.
2. `$PLUGIN_DATA/hermes-codex-plugin.sqlite3`.
3. Inferred Codex plugin data path from plugin cache.
4. `~/.hermes-codex-plugin/memory.sqlite3`.

## Architecture

```text
domain/         Entities, value objects, policies, and ports
application/    Commands, queries, DTOs, mappers, and recall services
infrastructure/ SQLite persistence, config, logging, and filesystem adapters
presentation/   CLI, hook, MCP, and formatting adapters
```

Commands and queries live in separate packages, and each handler has its own file.

## Development

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m compileall -q src tests hooks scripts
```

Expected result:

```text
Ran 52 tests
OK
```

## Privacy

- Memory stays local by default.
- No embeddings are used.
- Obvious tokens and secrets are redacted before storage.
- Redaction is not a full DLP system.

## License

MIT. See [LICENSE](LICENSE).
