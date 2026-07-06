import os
import tempfile
import unittest
from pathlib import Path

from hermes_codex_plugin.infrastructure.config import (
    default_db_path,
    infer_codex_plugin_data_path,
    load_settings,
)


class ConfigTest(unittest.TestCase):
    def test_infers_plugin_data_path_from_cache_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve() / "home" / "example"
            cwd = (
                root
                / ".codex"
                / "plugins"
                / "cache"
                / "hermes-codex-plugin"
                / "hermes-codex-plugin"
                / "0.1.3"
            )

            path = infer_codex_plugin_data_path(cwd)

            self.assertEqual(
                path,
                root
                / ".codex"
                / "plugins"
                / "data"
                / "hermes-codex-plugin-hermes-codex-plugin"
                / "hermes-codex-plugin.sqlite3",
            )

    def test_default_db_path_uses_plugin_root_when_plugin_data_is_missing(self) -> None:
        old_cwd = Path.cwd()
        old_env = {
            name: os.environ.get(name)
            for name in (
                "HERMES_CODEX_DB",
                "PLUGIN_DATA",
                "CLAUDE_PLUGIN_DATA",
                "PLUGIN_ROOT",
            )
        }
        try:
            for name in old_env:
                os.environ.pop(name, None)

            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir).resolve() / "home" / "example"
                os.environ["PLUGIN_ROOT"] = str(
                    root
                    / ".codex"
                    / "plugins"
                    / "cache"
                    / "hermes-codex-plugin"
                    / "hermes-codex-plugin"
                    / "0.1.4"
                )
                os.chdir(temp_dir)
                try:
                    self.assertEqual(
                        default_db_path(),
                        root
                        / ".codex"
                        / "plugins"
                        / "data"
                        / "hermes-codex-plugin-hermes-codex-plugin"
                        / "hermes-codex-plugin.sqlite3",
                    )
                finally:
                    os.chdir(old_cwd)
        finally:
            os.chdir(old_cwd)
            for name, value in old_env.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

    def test_explicit_db_path_takes_precedence(self) -> None:
        old_env = {
            name: os.environ.get(name)
            for name in (
                "HERMES_CODEX_DB",
                "PLUGIN_DATA",
                "CLAUDE_PLUGIN_DATA",
                "PLUGIN_ROOT",
            )
        }
        try:
            os.environ["HERMES_CODEX_DB"] = "/tmp/explicit-memory.sqlite3"
            os.environ["PLUGIN_DATA"] = "/tmp/plugin-data"

            self.assertEqual(default_db_path(), Path("/tmp/explicit-memory.sqlite3"))
        finally:
            for name, value in old_env.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

    def test_invalid_numeric_env_uses_default_and_boolean_env_parses_false(
        self,
    ) -> None:
        old_env = {
            name: os.environ.get(name)
            for name in (
                "HERMES_CODEX_DB",
                "HERMES_CODEX_RECALL_LIMIT",
                "HERMES_CODEX_DISABLED",
            )
        }
        try:
            os.environ["HERMES_CODEX_DB"] = "/tmp/settings.sqlite3"
            os.environ["HERMES_CODEX_RECALL_LIMIT"] = "not-a-number"
            os.environ["HERMES_CODEX_DISABLED"] = "off"

            settings = load_settings()

            self.assertEqual(settings.recall_limit, 5)
            self.assertFalse(settings.disabled)
        finally:
            for name, value in old_env.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value


if __name__ == "__main__":
    unittest.main()
