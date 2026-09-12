"""Abstract notification history persistence port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class NotificationHistoryPort(ABC):
    """Abstract port defining persistence operations for notification records."""

    @abstractmethod
    def load_history(self) -> dict[str, Any]:
        """Load the persisted notification history payload."""

    @abstractmethod
    def save_history(self, history: dict[str, Any]) -> None:
        """Persist the notification history payload."""


class InMemoryNotificationHistoryStore(NotificationHistoryPort):
    """In-memory history store used for isolated unit testing and fallback."""

    def __init__(self, initial_data: dict[str, Any] | None = None) -> None:
        self._data: dict[str, Any] = dict(initial_data or {
            "last_milestone1_date": "",
            "last_milestone2_date": "",
            "last_deadline_alarm_date": "",
            "last_reconciled_date": "",
            "dispatched_messages": [],
        })

    def load_history(self) -> dict[str, Any]:
        return self._data

    def save_history(self, history: dict[str, Any]) -> None:
        self._data = history
