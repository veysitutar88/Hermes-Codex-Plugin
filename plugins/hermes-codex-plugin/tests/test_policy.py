import unittest

from hermes_codex_plugin.domain.memory.policy import (
    global_memory_policy_context,
    search_hint_context,
)


class PolicyTest(unittest.TestCase):
    def test_global_policy_requires_memory_before_solving_tasks(self) -> None:
        policy = global_memory_policy_context()

        self.assertIn("Before solving a task", policy)
        self.assertIn("similar work", policy)
        self.assertIn("existing reusable skills", policy)
        self.assertIn("semantic judgment", policy)
        self.assertIn("multilingual rule", policy)
        self.assertIn("hermes_codex_propose_skill", policy)
        self.assertIn("hermes_codex_remember_summary", policy)
        self.assertIn("prefer summaries over raw chat transcripts", policy)
        self.assertIn("Apply durable rules", policy)
        self.assertIn("import placement", policy)

    def test_search_hint_uses_request_without_domain_expansion(self) -> None:
        prompt = (
            "Review this Python service and improve it according to "
            "DDD and code style rules"
        )

        hint = search_hint_context(prompt)

        self.assertIn(prompt, hint)
        self.assertNotIn("collection operations", hint)

    def test_search_hint_compacts_whitespace_and_limits_long_queries(self) -> None:
        prompt = "  first line\n\nsecond line  " + ("x" * 500)

        hint = search_hint_context(prompt)

        self.assertIn("first line second line", hint)
        self.assertLess(len(hint), 700)


if __name__ == "__main__":
    unittest.main()
