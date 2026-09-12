"""Notification module re-exporting ports and adapters for backward compatibility."""

from __future__ import annotations

from ports.notification_port import (
    DISCORD_COLOR_ALARM,
    DISCORD_COLOR_MILESTONE,
    DeleteResult,
    NotificationPort,
    NotificationResult,
    NullNotifier,
)
from runtime.discord_payload_builder import (
    build_alarm_payload,
    build_milestone_payload,
)
from runtime.discord_webhook_adapter import (
    DEFAULT_TIMEOUT_SECONDS,
    DiscordWebhookAdapter,
    inject_query_param,
)
from runtime.notifier_factory import (
    create_notification_history_store,
    create_notification_port,
    get_notifier,
    resolve_webhook_url,
)

# Backward-compatible function alias
_inject_query_param = inject_query_param

__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "DISCORD_COLOR_ALARM",
    "DISCORD_COLOR_MILESTONE",
    "DeleteResult",
    "DiscordWebhookAdapter",
    "NotificationPort",
    "NotificationResult",
    "NullNotifier",
    "build_alarm_payload",
    "build_milestone_payload",
    "create_notification_history_store",
    "create_notification_port",
    "get_notifier",
    "inject_query_param",
    "resolve_webhook_url",
]
