"""Abstract notification port defining system-to-operator notification capabilities."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping

DISCORD_COLOR_MILESTONE: int = 0x2ECC71  # Emerald Green
DISCORD_COLOR_ALARM: int = 0xE74C3C      # Bright Red


@dataclass(frozen=True)
class NotificationResult:
    """Encapsulates outcome of a notification dispatch."""
    success: bool
    external_message_id: str | None = None
    error: str | None = None

    def __bool__(self) -> bool:
        return self.success


@dataclass(frozen=True)
class DeleteResult:
    """Encapsulates outcome of a message deletion."""
    success: bool
    status_code: int = 200
    retry_after_seconds: float = 0.0
    error: str | None = None

    def __bool__(self) -> bool:
        return self.success


class NotificationPort(ABC):
    """Abstract interface defining system-to-operator notification capabilities."""

    @abstractmethod
    def notify_milestone(
        self,
        title: str,
        description: str,
        fields: Mapping[str, Any] | None = None,
        sync: bool = False,
        footer_text: str | None = None,
    ) -> NotificationResult:
        """Send an AUTOMATION_HEALTHY milestone notification."""

    @abstractmethod
    def notify_alarm(
        self,
        code: str,
        title: str,
        reason: str,
        details: Mapping[str, Any] | None = None,
        sync: bool = False,
        description: str | None = None,
        footer_text: str | None = None,
    ) -> NotificationResult:
        """Send an OPERATOR_ACTION_REQUIRED unrecoverable failure alarm."""

    @abstractmethod
    def delete_message(self, message_id: str) -> DeleteResult:
        """Delete a previously dispatched message by external ID."""


class NullNotifier(NotificationPort):
    """No-op notifier used when notifications are disabled or unconfigured."""

    def notify_milestone(
        self,
        title: str,
        description: str,
        fields: Mapping[str, Any] | None = None,
        sync: bool = False,
        footer_text: str | None = None,
    ) -> NotificationResult:
        logging.debug("[NullNotifier] Milestone suppressed: %s", title)
        return NotificationResult(success=False)

    def notify_alarm(
        self,
        code: str,
        title: str,
        reason: str,
        details: Mapping[str, Any] | None = None,
        sync: bool = False,
        description: str | None = None,
        footer_text: str | None = None,
    ) -> NotificationResult:
        logging.debug("[NullNotifier] Alarm suppressed (%s): %s", code, title)
        return NotificationResult(success=False)

    def delete_message(self, message_id: str) -> DeleteResult:
        logging.debug("[NullNotifier] Delete message suppressed: %s", message_id)
        return DeleteResult(success=False, error="NullNotifier")
