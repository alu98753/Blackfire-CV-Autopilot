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

        try:
            with self.path.open("r", encoding="utf-8") as file:
                loaded = json.load(file)
            if not isinstance(loaded, dict):
                raise ConfigLoadError(f"設定檔根節點必須是 JSON object: {self.path}")
            if self._validator is not None:
                self._validator(loaded)
        except (OSError, json.JSONDecodeError, ConfigLoadError) as error:
            return self._handle_error(ConfigLoadError(f"設定檔無法套用 ({error}): {self.path}"))

        self._snapshot = deepcopy(loaded)
        self._signature = signature
        self.last_error = None
        return True

    def _get_signature(self) -> tuple[int, int]:
        stat = self.path.stat()
        return stat.st_mtime_ns, stat.st_size

    def _handle_error(self, error: ConfigLoadError) -> bool:
        self.last_error = error
        if self._snapshot is None and self._default is None:
            raise error
        return False
