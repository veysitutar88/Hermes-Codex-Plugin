import os
from pathlib import Path
from typing import Optional

from pydantic import AliasChoices, Field, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


SQLITE_FILENAME = "hermes-codex-plugin.sqlite3"

_INT_DEFAULTS = {
    "recall_limit": 5,
    "recall_chars": 3000,
    "max_capture_chars": 200000,
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.getenv("HERMES_CODEX_ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="HERMES_CODEX_",
    )

    db_path: Optional[Path] = Field(default=None, validation_alias="HERMES_CODEX_DB")
    plugin_data: Optional[Path] = Field(
        default=None,
        validation_alias=AliasChoices("PLUGIN_DATA", "CLAUDE_PLUGIN_DATA"),
        exclude=True,
    )
    plugin_root: Optional[Path] = Field(
        default=None,
        validation_alias="PLUGIN_ROOT",
        exclude=True,
    )
    recall_limit: int = 5
    recall_chars: int = 3000
    max_capture_chars: int = 200000
    capture_assistant: bool = True
    disabled: bool = False

    @field_validator("db_path", "plugin_data", "plugin_root", mode="after")
    @classmethod
    def _expand_path(cls, value: Optional[Path]) -> Optional[Path]:
        if value is None:
            return None
        return value.expanduser()

    @field_validator("recall_limit", "recall_chars", "max_capture_chars", mode="before")
    @classmethod
    def _int_or_default(cls, value: object, info: ValidationInfo) -> int:
        default = _INT_DEFAULTS[info.field_name]
        if value in (None, ""):
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @model_validator(mode="after")
    def _resolve_db_path(self) -> "Settings":
        if self.db_path is None:
            self.db_path = default_db_path(
                plugin_data=self.plugin_data,
                plugin_root=self.plugin_root,
            )
        return self


def default_db_path(
    explicit_db_path: Optional[Path] = None,
    plugin_data: Optional[Path] = None,
    plugin_root: Optional[Path] = None,
    cwd: Optional[Path] = None,
) -> Path:
    explicit = explicit_db_path or _path_from_env("HERMES_CODEX_DB")
    if explicit:
        return Path(explicit).expanduser()

    plugin_data = (
        plugin_data
        or _path_from_env("PLUGIN_DATA")
        or _path_from_env("CLAUDE_PLUGIN_DATA")
    )
    if plugin_data:
        return Path(plugin_data).expanduser() / SQLITE_FILENAME

    inferred_plugin_data = infer_codex_plugin_data_path(cwd or Path.cwd())
    if inferred_plugin_data is not None:
        return inferred_plugin_data

    plugin_root = plugin_root or _path_from_env("PLUGIN_ROOT")
    if plugin_root:
        inferred_plugin_data = infer_codex_plugin_data_path(Path(plugin_root))
        if inferred_plugin_data is not None:
            return inferred_plugin_data

    return Path.home() / ".hermes-codex-plugin" / "memory.sqlite3"


def _path_from_env(name: str) -> Optional[Path]:
    raw = os.environ.get(name)
    if not raw:
        return None
    return Path(raw).expanduser()


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
            / SQLITE_FILENAME
        )
    return None


def load_settings() -> Settings:
    return Settings()
