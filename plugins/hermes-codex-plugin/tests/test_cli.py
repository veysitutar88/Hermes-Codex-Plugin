import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from hermes_codex_plugin.presentation.cli.main import main


class CliTest(unittest.TestCase):
    def test_cli_remember_search_and_forget_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_db = os.environ.get("HERMES_CODEX_DB")
            os.environ["HERMES_CODEX_DB"] = str(Path(tmp) / "memory.sqlite3")
            try:
                remember_output = run_cli(
                    ["remember", "CLI round trip memory.", "--kind", "rule"]
                )
                entry_id = int(remember_output.strip().split("#")[1])

                search_output = run_cli(["search", "round trip"])
                self.assertIn("CLI round trip memory.", search_output)

                forget_output = run_cli(["forget", str(entry_id)])
                self.assertEqual(forget_output.strip(), "deleted")

                search_after_delete = run_cli(["search", "round trip"])
                self.assertEqual(search_after_delete.strip(), "No matching memories.")
            finally:
                if old_db is None:
                    os.environ.pop("HERMES_CODEX_DB", None)
                else:
                    os.environ["HERMES_CODEX_DB"] = old_db


def run_cli(argv):
    output = StringIO()
    with redirect_stdout(output):
        main(argv)
    return output.getvalue()


if __name__ == "__main__":
    unittest.main()
