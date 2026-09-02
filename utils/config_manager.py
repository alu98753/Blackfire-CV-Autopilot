"""Shared, transactional configuration loading with lightweight hot reload."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Callable


class ConfigLoadError(ValueError):
    """Raised when a configuration file cannot produce a valid snapshot."""


class JsonConfigManager:
    """Own one JSON file and only publish complete, valid configuration snapshots.

    Callers receive copies, so an invalid edit or a caller mutation cannot corrupt
    the last known-good configuration used by a running automation process.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        default: dict[str, Any] | None = None,
        validator: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.path = Path(path)
        self._default = deepcopy(default) if default is not None else None
        self._validator = validator
        self._snapshot: dict[str, Any] | None = None
        self._signature: tuple[int, int] | None = None
        self._failed_signature: tuple[int, int] | None = None
        self.last_error: ConfigLoadError | None = None

    def snapshot(self, *, force: bool = False) -> dict[str, Any]:
        """Return the latest valid snapshot, reloading only after a file change."""
        self.reload_if_changed(force=force)
        if self._snapshot is None:
            if self._default is not None:
                return deepcopy(self._default)
            raise ConfigLoadError(f"設定檔尚未成功載入: {self.path}")
        return deepcopy(self._snapshot)

    def reload_if_changed(self, *, force: bool = False) -> bool:
        """Publish a new snapshot when changed; retain the old one on failure."""
        try:
            signature = self._get_signature()
        except OSError as error:
            return self._handle_error(ConfigLoadError(f"無法讀取設定檔狀態 ({error}): {self.path}"))

        if not force and self._snapshot is not None and signature == self._signature:
            return False
        if not force and signature == self._failed_signature:
            return False

        try:
            loaded = self._read_file()
            if not isinstance(loaded, dict):
                raise ConfigLoadError(f"設定檔根節點必須是 JSON object: {self.path}")
            if self._validator is not None:
                self._validator(loaded)
        except (OSError, ValueError, TypeError) as error:
            self._failed_signature = signature
            return self._handle_error(ConfigLoadError(f"設定檔無法套用 ({error}): {self.path}"))

        self._snapshot = deepcopy(loaded)
        self._signature = signature
        self._failed_signature = None
        self.last_error = None
        return True

    def _get_signature(self) -> tuple[int, int]:
        stat = self.path.stat()
        return stat.st_mtime_ns, stat.st_size

    def _read_file(self) -> dict[str, Any]:
        with self.path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _handle_error(self, error: ConfigLoadError) -> bool:
        self.last_error = error
        if self._snapshot is None and self._default is None:
            raise error
        return False


class TomlConfigManager(JsonConfigManager):
    """The same transactional hot-reload contract for TOML configuration."""

    def _read_file(self) -> dict[str, Any]:
        import tomllib

        with self.path.open("rb") as file:
            return tomllib.load(file)


def format_toml_value(val: Any) -> str:
    """Format scalar or list value into TOML syntax string."""
    if isinstance(val, bool):
        return "true" if val else "false"
    elif isinstance(val, (int, float)):
        return str(val)
    elif isinstance(val, str):
        escaped = val.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    elif isinstance(val, list):
        items = [format_toml_value(x) for x in val]
        return f"[{', '.join(items)}]"
    return str(val)


def dump_toml_dict(data: dict[str, Any]) -> str:
    """Serialize nested dictionary into clean, standard TOML string."""
    lines: list[str] = []

    # 1. Top-level scalar/list properties
    for k, v in data.items():
        if not isinstance(v, dict):
            lines.append(f"{k} = {format_toml_value(v)}")

    if lines:
        lines.append("")

    # 2. Nested sections
    def dump_section(prefix: list[str], section_dict: dict[str, Any]):
        section_scalars: list[tuple[str, Any]] = []
        nested_subsections: list[tuple[str, dict[str, Any]]] = []
        for k, v in section_dict.items():
            if isinstance(v, dict):
                nested_subsections.append((k, v))
            else:
                section_scalars.append((k, v))

        if section_scalars or not nested_subsections:
            header = ".".join(prefix)
            lines.append(f"[{header}]")
            for k, v in section_scalars:
                lines.append(f"{k} = {format_toml_value(v)}")
            lines.append("")

        for sub_k, sub_v in nested_subsections:
            dump_section(prefix + [sub_k], sub_v)

    for section_name, section_val in data.items():
        if isinstance(section_val, dict):
            dump_section([section_name], section_val)

    return "\n".join(lines).strip() + "\n"
