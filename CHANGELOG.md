# Changelog

## 0.10.2

- Move runtime configuration to `pydantic-settings` with flat environment variables.
- Make config path tests independent from the current Codex plugin cache working directory.

## 0.10.1

- Replace the square mark with a retro block wordmark inspired by the Hermes Agent banner style.
- Keep visible logo content limited to the brand mark while README text carries the project description.

## 0.10.0

- Rename the public project, plugin package, MCP server, Python package, and skill to Hermes Codex Plugin.
- Replace the wide wordmark SVG with a logo-only AI agent mark.
- Shorten MCP tool names to the `hermes_codex_*` namespace.
- Rename environment variables to the `HERMES_CODEX_*` namespace.

## 0.9.0

- Add open-source project branding, logo, badges, CI workflow, and contributor docs.
- Remove `print()` calls from source code.
- Add safe logging support with `loguru` when available.
- Declare package metadata and project URLs for open-source distribution.

## 0.8.0

- Keep plugin source, prompts, policies, and tests English-only.
- Remove Russian text from hook policy and test fixtures.

## 0.7.0

- Split application commands and queries into separate packages.
- Move each command/query handler into its own file.

## 0.6.0

- Add DTOs and explicit mapper classes.
- Move skill Markdown rendering into presentation code.

## 0.5.0

- Remove alias and re-export compatibility modules.
- Update imports to direct module paths.

## 0.4.0

- Replace structure-only tests with behavioral edge-case tests.
- Remove trivial entity unwrap properties.

## 0.3.0

- Restructure the package into domain, application, infrastructure, and presentation layers.

## 0.2.0

- Remove hardcoded memory-first keyword expansion.
- Use the raw user request as the primary memory query.

## 0.1.0

- Initial local-first memory MVP with hooks, MCP tools, SQLite FTS, and skill drafts.
