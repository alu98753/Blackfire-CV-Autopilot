"""Outbound adapter delivering domain notifications to Discord via webhook."""

from __future__ import annotations

import json
import logging
import threading
import urllib.error
import urllib.request
from typing import Any, Mapping
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from ports.notification_port import (
    DeleteResult,
    NotificationPort,
    NotificationResult,
)
from runtime.discord_payload_builder import (
    build_alarm_payload,
    build_milestone_payload,
)

DEFAULT_TIMEOUT_SECONDS: float = 3.0


def inject_query_param(url: str, key: str, value: str) -> str:
    """Safely append or update a query parameter on a URL without breaking existing query strings."""
    if not url:
        return url
    parsed = urlparse(url)
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    filtered_pairs = [(k, v) for k, v in query_pairs if k != key]
    filtered_pairs.append((key, value))
    new_query = urlencode(filtered_pairs)
    return urlunparse(parsed._replace(query=new_query))


class DiscordWebhookAdapter(NotificationPort):
    """Outbound adapter delivering domain notifications to Discord via webhook."""

    def __init__(
        self,
        webhook_url: str,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        profile: str | None = None,
        language: str | None = None,
    ) -> None:
        self.webhook_url = webhook_url.strip()
        self.timeout_seconds = max(0.5, float(timeout_seconds))
        self.profile = profile
        if language is not None:
            from runtime.notification_i18n import normalize_language
            self.language = normalize_language(language)
        else:
            from config import get_notification_language
            self.language = get_notification_language(profile=self.profile)

    def notify_milestone(
        self,
        title: str,
        description: str,
        fields: Mapping[str, Any] | None = None,
        sync: bool = False,
        footer_text: str | None = None,
    ) -> NotificationResult:
        payload = build_milestone_payload(
            title=title,
            description=description,
            fields=fields,
            footer_text=footer_text,
            language=self.language,
        )
        return self._dispatch(payload, sync=sync)

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
        payload = build_alarm_payload(
            code=code,
            title=title,
            reason=reason,
            details=details,
            description=description,
            footer_text=footer_text,
            language=self.language,
        )
        return self._dispatch(payload, sync=sync)

    def delete_message(self, message_id: str) -> DeleteResult:
        """Delete a previously dispatched webhook message.

        204 (deleted) and 404 (already gone) both satisfy the desired state.
        """
        if not self.webhook_url:
            return DeleteResult(success=False, error="Empty webhook URL")
        if not message_id:
            return DeleteResult(success=False, error="Empty message_id")

        parsed = urlparse(self.webhook_url)
        base_path = parsed.path.rstrip('/')
        new_path = f"{base_path}/messages/{message_id.strip()}"
        delete_url = urlunparse(parsed._replace(path=new_path))
        req = urllib.request.Request(
            delete_url,
            headers={
                "User-Agent": "BlackfireCrusade-Notifier/1.0",
            },
            method="DELETE",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                status = resp.status
                if status in (200, 204):
                    logging.info("[DiscordNotifier] Message %s deleted successfully (status: %d).", message_id, status)
                    return DeleteResult(success=True, status_code=status)
                return DeleteResult(success=False, status_code=status, error=f"Unexpected status {status}")
        except urllib.error.HTTPError as e:
            status = e.code
            if status == 404:
                logging.info("[DiscordNotifier] Message %s already deleted (404 Not Found), treated as success.", message_id)
                return DeleteResult(success=True, status_code=404)
            if status == 429:
                retry_after = 0.0
                try:
                    body = e.read().decode("utf-8", errors="replace")
                    data = json.loads(body)
                    retry_after = float(data.get("retry_after", 0.0))
                except Exception:
                    pass
                if not retry_after and "Retry-After" in e.headers:
                    try:
                        retry_after = float(e.headers["Retry-After"])
                    except Exception:
                        pass
                logging.warning("[DiscordNotifier] Rate limited deleting message %s (429). Retry after: %.2fs", message_id, retry_after)
                return DeleteResult(success=False, status_code=429, retry_after_seconds=retry_after, error="Rate limited")
            logging.warning("[DiscordNotifier] HTTP error deleting message %s (%d): %s", message_id, status, e.reason)
            return DeleteResult(success=False, status_code=status, error=str(e.reason))
        except Exception as e:
            logging.warning("[DiscordNotifier] Network error deleting message %s: %s", message_id, e)
            return DeleteResult(success=False, error=str(e))

    def _dispatch(self, payload: dict[str, Any], sync: bool) -> NotificationResult:
        if sync:
            return self._post_payload(payload)

        # Asynchronous dispatch cannot return an external_message_id to the caller.
        # Callers requiring message tracking and daily reconciliation MUST specify sync=True.
        worker = threading.Thread(
            target=self._post_payload,
            args=(payload,),
            daemon=True,
            name="DiscordNotificationThread",
        )
        worker.start()
        return NotificationResult(success=True)

    def _post_payload(self, payload: dict[str, Any]) -> NotificationResult:
        if not self.webhook_url:
            logging.warning("[DiscordNotifier] Webhook URL is empty; skipping notification.")
            return NotificationResult(success=False, error="Empty webhook URL")

        post_url = inject_query_param(self.webhook_url, "wait", "true")
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            post_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "BlackfireCrusade-Notifier/1.0",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                status = resp.status
                if status != 200:
                    logging.warning(
                        "[DiscordNotifier] Delivery protocol failure: Expected HTTP 200 with wait=true, got %d.",
                        status,
                    )
                    return NotificationResult(
                        success=False,
                        error=f"Expected HTTP 200 with wait=true, got {status}",
                    )

                raw_data = resp.read()
                try:
                    resp_json = json.loads(raw_data.decode("utf-8"))
                except Exception as exc:
                    logging.warning("[DiscordNotifier] Failed to decode JSON response from Discord: %s", exc)
                    return NotificationResult(
                        success=False,
                        error=f"Invalid Discord response body: {exc}",
                    )

                if not isinstance(resp_json, dict) or not resp_json.get("id"):
                    logging.warning("[DiscordNotifier] Discord response missing message ID: %s", resp_json)
                    return NotificationResult(
                        success=False,
                        error="Discord response missing message id",
                    )

                message_id = str(resp_json["id"])
                logging.info(
                    "[DiscordNotifier] Notification delivered successfully (status: %d, id: %s).",
                    status,
                    message_id,
                )
                return NotificationResult(success=True, external_message_id=message_id)
        except urllib.error.HTTPError as ex:
            logging.warning("[DiscordNotifier] HTTP error delivering notification (%d): %s", ex.code, ex.reason)
            return NotificationResult(success=False, error=str(ex.reason))
        except urllib.error.URLError as ex:
            logging.warning("[DiscordNotifier] Network error delivering notification: %s", ex.reason)
            return NotificationResult(success=False, error=str(ex.reason))
        except Exception as ex:
            logging.warning("[DiscordNotifier] Unexpected failure delivering notification: %s", ex)
            return NotificationResult(success=False, error=str(ex))
