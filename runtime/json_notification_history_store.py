"""Filesystem JSON adapter implementing NotificationHistoryPort."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from config import USER_DATA_DIR
from ports.notification_history_port import NotificationHistoryPort
from runtime.incident_journal import normalize_profile


class JsonNotificationHistoryStore(NotificationHistoryPort):
    """Persists notification history and dispatched message records to a JSON file."""

    def __init__(
        self,
        profile: str | None = None,
        history_file_path: str | None = None,
    ) -> None:
        self.profile = normalize_profile(profile)
        if history_file_path:
            self.history_file = history_file_path
        else:
            runtime_dir = os.path.join(USER_DATA_DIR, self.profile, "runtime")
            self.history_file = os.path.join(runtime_dir, "notification_history.json")
        self._cache: dict[str, Any] | None = None

    def load_history(self) -> dict[str, Any]:
        if self._cache is not None:
            return self._cache

        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        if "dispatched_messages" not in data or not isinstance(data["dispatched_messages"], list):
                            data["dispatched_messages"] = []
                        self._cache = data
                        return self._cache
            except Exception as e:
                logging.warning("[JsonNotificationHistoryStore] Failed to load history file (%s): %s", self.history_file, e)

        self._cache = {
            "last_milestone1_date": "",
            "last_milestone2_date": "",
            "last_deadline_alarm_date": "",
            "last_reconciled_date": "",
            "dispatched_messages": [],
        }
        return self._cache

    def save_history(self, history: dict[str, Any]) -> None:
        target_dir = os.path.dirname(self.history_file)
        tmp_file = f"{self.history_file}.tmp"
        try:
            if target_dir:
                os.makedirs(target_dir, exist_ok=True)
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_file, self.history_file)
            self._cache = history
        except Exception as e:
            if os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except Exception:
                    pass
            logging.warning("[JsonNotificationHistoryStore] Failed to save history file (%s): %s", self.history_file, e)
