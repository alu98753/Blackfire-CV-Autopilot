"""Factory functions for resolving and creating notification ports and history stores."""

from __future__ import annotations

import os
from typing import Mapping

from ports.notification_history_port import NotificationHistoryPort
from ports.notification_port import NotificationPort, NullNotifier
from runtime.discord_webhook_adapter import DiscordWebhookAdapter
from runtime.json_notification_history_store import JsonNotificationHistoryStore


def resolve_webhook_url(
    profile: str | None = None,
    env_vars: Mapping[str, str] | None = None,
) -> str | None:
    """Resolve Discord Webhook URL following precedence: env var > profile TOML > defaults TOML."""
    env = env_vars if env_vars is not None else os.environ
    env_url = env.get("DISCORD_WEBHOOK_URL", "").strip()
    if env_url:
        return env_url

    try:
        from config import get_notification_webhook_url
        toml_url = get_notification_webhook_url(profile=profile).strip()
        if toml_url:
            return toml_url
    except Exception:
        pass

    return None


def create_notification_port(
    profile: str | None = None,
    webhook_url: str | None = None,
) -> NotificationPort:
    """Instantiate and return the appropriate NotificationPort implementation."""
    url = (webhook_url or "").strip() or resolve_webhook_url(profile=profile)
    if not url:
        return NullNotifier()
    return DiscordWebhookAdapter(webhook_url=url, profile=profile)


def create_notification_history_store(
    profile: str | None = None,
    history_file_path: str | None = None,
) -> NotificationHistoryPort:
    """Instantiate and return the JsonNotificationHistoryStore."""
    return JsonNotificationHistoryStore(profile=profile, history_file_path=history_file_path)


# Backward-compatible alias
get_notifier = create_notification_port
