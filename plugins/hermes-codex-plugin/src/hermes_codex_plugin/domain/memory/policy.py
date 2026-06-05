GLOBAL_MEMORY_POLICY = (
    "Hermes Codex Plugin global memory policy: local memory is a standing source of "
    "user preferences, project conventions, architectural rules, prior decisions, and "
    "workflow rules. For every user request, before assuming missing context or asking "
    "the user to repeat a rule, check whether the needed context is already present in "
    "the current prompt/thread. If it is not, consult Hermes Codex Plugin memory first. "
    "Before solving a task, check memory for similar work, existing reusable skills, "
    "prior decisions, and user/project rules that should guide the implementation. "
    "If MCP tools are callable, call `hermes_codex_search_chats` to search across "
    "previous chats/sessions, or `hermes_codex_search` for a narrower memory search. "
    "Use skills for reusable procedures and chat memory for facts, prior decisions, and "
    "context from earlier conversations. Use semantic judgment, not English-only keyword "
    "matching, when deciding whether a remembered multilingual rule should become a skill "
    "draft; repeated workflow rules are good candidates for `hermes_codex_propose_skill`, "
    "but writing a skill still requires user intent or review. After substantial tasks, "
    "compose a concise structured summary and call `hermes_codex_remember_summary` when "
    "MCP tools are callable; prefer summaries over raw chat transcripts for long-term "
    "memory. Apply durable rules from "
    "memory as constraints while editing code, such as style rules, architecture "
    "boundaries, or import placement. "
    "If MCP tools are not callable, apply the durable memory entries injected by this hook. "
    "If memory has no relevant result, continue with "
    "the normal Codex workflow: inspect the repository, reason from the current context, "
    "and ask the user only when the missing information cannot be discovered. Do not wait "
    "for the user to explicitly ask you to search memory."
)


def search_hint_context(query: str) -> str:
    compact_query = " ".join(query.split())[:400]
    return (
        "Hermes Codex Plugin search hint: use this user request as the primary memory "
        "query: `{}`. Prefer exact terms from the request, then add project-specific "
        "terms only if the current context provides them. Do not use hardcoded domain "
        "keywords unless they appear in the request or recalled memory."
    ).format(compact_query)


def global_memory_policy_context() -> str:
    return GLOBAL_MEMORY_POLICY
