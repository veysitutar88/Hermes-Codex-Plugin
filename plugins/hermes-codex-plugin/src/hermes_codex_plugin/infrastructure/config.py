import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


@dataclass(frozen=True)
class Settings:
    db_path: Path
    recall_limit: int = 5
    recall_chars: int = 3000
    max_capture_chars: int = 200000
    capture_assistant: bool = True
    disabled: bool = False


def default_db_path() -> Path:
    explicit = os.environ.get("HERMES_CODEX_DB")
    if explicit:
        return Path(explicit).expanduser()

    plugin_data = os.environ.get("PLUGIN_DATA") or os.environ.get("CLAUDE_PLUGIN_DATA")
    if plugin_data:
        return Path(plugin_data).expanduser() / "hermes-codex-plugin.sqlite3"

    inferred_plugin_data = infer_codex_plugin_data_path(Path.cwd())
    if inferred_plugin_data is not None:
        return inferred_plugin_data

    plugin_root = os.environ.get("PLUGIN_ROOT")
    if plugin_root:
        inferred_plugin_data = infer_codex_plugin_data_path(Path(plugin_root))
        if inferred_plugin_data is not None:
            return inferred_plugin_data

    return Path.home() / ".hermes-codex-plugin" / "memory.sqlite3"


def infer_codex_plugin_data_path(cwd: Path) -> Optional[Path]:
    parts = cwd.expanduser().resolve().parts
    marker = (".codex", "plugins", "cache")
    for index in range(0, len(parts) - len(marker) - 2):
        if tuple(parts[index : index + len(marker)]) != marker:
            continue
        marketplace_index = index + len(marker)
        plugin_index = marketplace_index + 1
        if len(parts) <= plugin_index:
            return None
        marketplace = parts[marketplace_index]
        plugin = parts[plugin_index]
        if not marketplace or not plugin:
            return None
        home = Path(*parts[:index]) if index else Path("/")
        return (
            home
            / ".codex"
            / "plugins"
            / "data"
            / "{}-{}".format(marketplace, plugin)
            / "hermes-codex-plugin.sqlite3"
        )
    return None


def load_settings() -> Settings:
    return Settings(
        db_path=default_db_path(),
        recall_limit=_int_env("HERMES_CODEX_RECALL_LIMIT", 5),
        recall_chars=_int_env("HERMES_CODEX_RECALL_CHARS", 3000),
        max_capture_chars=_int_env("HERMES_CODEX_MAX_CAPTURE_CHARS", 200000),
        capture_assistant=_bool_env("HERMES_CODEX_CAPTURE_ASSISTANT", True),
        disabled=_bool_env("HERMES_CODEX_DISABLED", False),
    )
