import os
import tempfile
import unittest
from pathlib import Path

from hermes_codex_plugin import __version__
from hermes_codex_plugin.infrastructure.db.gateways.memory import MemoryRepoGateway
from hermes_codex_plugin.presentation.mcp.server import open_mcp_server


class MCPServerTest(unittest.IsolatedAsyncioTestCase):
    async def test_initialize_returns_server_info(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["HERMES_CODEX_DB"] = str(Path(tmp) / "memory.sqlite3")
            try:
                async with open_mcp_server() as server:
                    response = await server.handle_message(
                        {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "initialize",
                            "params": {"protocolVersion": "2024-11-05"},
                        }
                    )

                self.assertEqual(
                    response["result"]["serverInfo"]["version"], __version__
                )
                self.assertIn(
                    "hermes_codex_search_chats", response["result"]["instructions"]
                )
            finally:
                os.environ.pop("HERMES_CODEX_DB", None)

    async def test_tools_list_contains_memory_tools(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["HERMES_CODEX_DB"] = str(Path(tmp) / "memory.sqlite3")
            try:
                async with open_mcp_server() as server:
                    response = await server.handle_message(
                        {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
                    )

                tool_names = {tool["name"] for tool in response["result"]["tools"]}
                self.assertIn("hermes_codex_search", tool_names)
                self.assertIn("hermes_codex_search_chats", tool_names)
                self.assertIn("hermes_codex_remember", tool_names)
                self.assertIn("hermes_codex_remember_summary", tool_names)
                self.assertIn("hermes_codex_forget", tool_names)
            finally:
                os.environ.pop("HERMES_CODEX_DB", None)

    async def test_tools_call_search(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["HERMES_CODEX_DB"] = str(Path(tmp) / "memory.sqlite3")
            try:
                async with open_mcp_server() as server:
                    await server.tool_remember(
                        {
                            "content": "Always run unittest before release.",
                            "kind": "rule",
                        }
                    )

                    response = await server.handle_message(
                        {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "tools/call",
                            "params": {
                                "name": "hermes_codex_search",
                                "arguments": {"query": "unittest release"},
                            },
                        }
                    )

                text = response["result"]["content"][0]["text"]
                self.assertIn("unittest", text)
            finally:
                os.environ.pop("HERMES_CODEX_DB", None)

    async def test_search_chats_ignores_current_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["HERMES_CODEX_DB"] = str(Path(tmp) / "memory.sqlite3")
            try:
                async with open_mcp_server() as server:
                    async with server.session_maker() as session:
                        repo = MemoryRepoGateway(session, server.settings.db_path)
                        await repo.add_entry(
                            "Previous chat fact: HCP_MCP_CROSS_CHAT_FACT.",
                            kind="assistant",
                            session_id="old-chat",
                            cwd="/tmp/old-project",
                        )
                        await session.commit()

                    response = await server.handle_message(
                        {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "tools/call",
                            "params": {
                                "name": "hermes_codex_search_chats",
                                "arguments": {"query": "HCP_MCP_CROSS_CHAT_FACT"},
                            },
                        }
                    )

                text = response["result"]["content"][0]["text"]
                self.assertIn("HCP_MCP_CROSS_CHAT_FACT", text)
                self.assertIn("old-chat", text)
            finally:
                os.environ.pop("HERMES_CODEX_DB", None)

    async def test_remember_stats_and_forget_tools_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["HERMES_CODEX_DB"] = str(Path(tmp) / "memory.sqlite3")
            try:
                async with open_mcp_server() as server:
                    remember_response = await server.handle_message(
                        {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "tools/call",
                            "params": {
                                "name": "hermes_codex_remember",
                                "arguments": {
                                    "content": "MCP round trip memory.",
                                    "kind": "rule",
                                },
                            },
                        }
                    )
                    remember_text = remember_response["result"]["content"][0]["text"]
                    entry_id = int(remember_text.split("#")[1])

                    stats_response = await server.handle_message(
                        {
                            "jsonrpc": "2.0",
                            "id": 2,
                            "method": "tools/call",
                            "params": {
                                "name": "hermes_codex_stats",
                                "arguments": {},
                            },
                        }
                    )
                    stats_text = stats_response["result"]["content"][0]["text"]
                    self.assertIn('"total_entries": 1', stats_text)

                    forget_response = await server.handle_message(
                        {
                            "jsonrpc": "2.0",
                            "id": 3,
                            "method": "tools/call",
                            "params": {
                                "name": "hermes_codex_forget",
                                "arguments": {"id": entry_id},
                            },
                        }
                    )

                self.assertIn(
                    "Deleted entry #{}".format(entry_id),
                    forget_response["result"]["content"][0]["text"],
                )
            finally:
                os.environ.pop("HERMES_CODEX_DB", None)

    async def test_remember_summary_tool_saves_structured_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["HERMES_CODEX_DB"] = str(Path(tmp) / "memory.sqlite3")
            try:
                async with open_mcp_server() as server:
                    remember_response = await server.handle_message(
                        {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "tools/call",
                            "params": {
                                "name": "hermes_codex_remember_summary",
                                "arguments": {
                                    "goal": "Migrate memory storage to async SQLAlchemy.",
                                    "outcome": "Async reader and repo gateways were added.",
                                    "decisions": [
                                        "Keep DB sessions outside repositories."
                                    ],
                                    "rules_learned": [
                                        "Use class-based domain services."
                                    ],
                                    "files_touched": ["application/memory/recall.py"],
                                    "open_questions": [
                                        "Disable raw transcript capture by default?"
                                    ],
                                    "keywords": ["async SQLAlchemy", "summary memory"],
                                    "cwd": "/tmp/project",
                                },
                            },
                        }
                    )
                    remember_text = remember_response["result"]["content"][0]["text"]

                    search_response = await server.handle_message(
                        {
                            "jsonrpc": "2.0",
                            "id": 2,
                            "method": "tools/call",
                            "params": {
                                "name": "hermes_codex_search",
                                "arguments": {
                                    "query": "async SQLAlchemy summary",
                                    "cwd": "/tmp/project",
                                },
                            },
                        }
                    )

                self.assertIn("Remembered summary #", remember_text)
                search_text = search_response["result"]["content"][0]["text"]
                self.assertIn("[summary/session]", search_text)
                self.assertIn("Use class-based domain services", search_text)
            finally:
                os.environ.pop("HERMES_CODEX_DB", None)

    async def test_unknown_method_and_tool_return_jsonrpc_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["HERMES_CODEX_DB"] = str(Path(tmp) / "memory.sqlite3")
            try:
                async with open_mcp_server() as server:
                    unknown_method = await server.handle_message(
                        {"jsonrpc": "2.0", "id": 1, "method": "missing/method"}
                    )
                    unknown_tool = await server.handle_message(
                        {
                            "jsonrpc": "2.0",
                            "id": 2,
                            "method": "tools/call",
                            "params": {"name": "missing_tool", "arguments": {}},
                        }
                    )

                self.assertEqual(unknown_method["error"]["code"], -32601)
                self.assertEqual(unknown_tool["error"]["code"], -32601)
            finally:
                os.environ.pop("HERMES_CODEX_DB", None)

    async def test_notification_without_id_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["HERMES_CODEX_DB"] = str(Path(tmp) / "memory.sqlite3")
            try:
                async with open_mcp_server() as server:
                    response = await server.handle_message(
                        {"jsonrpc": "2.0", "method": "notifications/initialized"}
                    )

                self.assertIsNone(response)
            finally:
                os.environ.pop("HERMES_CODEX_DB", None)

    async def test_remember_tool_rejects_empty_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["HERMES_CODEX_DB"] = str(Path(tmp) / "memory.sqlite3")
            try:
                async with open_mcp_server() as server:
                    with self.assertRaises(ValueError):
                        await server.tool_remember({"content": "   "})
            finally:
                os.environ.pop("HERMES_CODEX_DB", None)

    async def test_remember_summary_tool_rejects_empty_goal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["HERMES_CODEX_DB"] = str(Path(tmp) / "memory.sqlite3")
            try:
                async with open_mcp_server() as server:
                    with self.assertRaises(ValueError):
                        await server.tool_remember_summary({"goal": "   "})
            finally:
                os.environ.pop("HERMES_CODEX_DB", None)


if __name__ == "__main__":
    unittest.main()
