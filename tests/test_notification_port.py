"""Unit tests for NotificationPort and DiscordWebhookAdapter."""

from __future__ import annotations

import io
import json
import os
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

from runtime.notifier import (
    DISCORD_COLOR_ALARM,
    DISCORD_COLOR_MILESTONE,
    DiscordWebhookAdapter,
    NotificationPort,
    NullNotifier,
    get_notifier,
    resolve_webhook_url,
    send_test_notifications,
)


class TestNotificationPort(unittest.TestCase):
    """Verify behavior of NotificationPort implementations and webhook delivery."""

    def test_null_notifier_is_safe_noop(self):
        notifier = NullNotifier()
        self.assertIsInstance(notifier, NotificationPort)
        self.assertFalse(notifier.notify_milestone("Test Title", "Test Desc"))
        self.assertFalse(notifier.notify_alarm("ERR_CODE", "Test Title", "Test Reason"))

    @patch("urllib.request.urlopen")
    def test_discord_webhook_adapter_milestone_payload(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        adapter = DiscordWebhookAdapter(webhook_url="https://discord.com/api/webhooks/test/dummy")
        result = adapter.notify_milestone(
            title="Daily Claim Phase Completed",
            description="All town subflows finished.",
            fields={"Quests": ["Quest 1", "Quest 2"], "Count": 5},
            sync=True,
        )

        self.assertTrue(result)
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.full_url, "https://discord.com/api/webhooks/test/dummy")
        self.assertEqual(req.headers["Content-type"], "application/json")

        payload = json.loads(req.data.decode("utf-8"))
        self.assertIn("embeds", payload)
        embed = payload["embeds"][0]
        self.assertIn("Daily Claim Phase Completed", embed["title"])
        self.assertEqual(embed["color"], DISCORD_COLOR_MILESTONE)
        self.assertEqual(len(embed["fields"]), 2)
        self.assertEqual(embed["fields"][0]["name"], "Quests")
        self.assertEqual(embed["fields"][0]["value"], '["Quest 1", "Quest 2"]')

    @patch("urllib.request.urlopen")
    def test_discord_webhook_adapter_alarm_payload(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        adapter = DiscordWebhookAdapter(webhook_url="https://discord.com/api/webhooks/test/dummy", language="en")
        result = adapter.notify_alarm(
            code="CRASH_LIMIT_EXCEEDED",
            title="Supervisor Crash Loop",
            reason="Exceeded 5 restarts in 10 minutes",
            details={"Restarts": 5},
            sync=True,
        )

        self.assertTrue(result)
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode("utf-8"))
        embed = payload["embeds"][0]
        self.assertIn("Supervisor Crash Loop", embed["title"])
        self.assertEqual(embed["color"], DISCORD_COLOR_ALARM)
        field_dict = {f["name"]: f["value"] for f in embed["fields"]}
        self.assertEqual(field_dict["Alarm Code"], "CRASH_LIMIT_EXCEEDED")
        self.assertEqual(field_dict["Reason"], "Exceeded 5 restarts in 10 minutes")
        self.assertEqual(field_dict["Restarts"], "5")

    def test_empty_webhook_url_skips_dispatch(self):
        adapter = DiscordWebhookAdapter(webhook_url="")
        self.assertFalse(adapter.notify_milestone("Title", "Desc", sync=True))
        self.assertFalse(adapter.notify_alarm("CODE", "Title", "Reason", sync=True))

    @patch("urllib.request.urlopen")
    def test_http_error_does_not_raise(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="http://test", code=404, msg="Not Found", hdrs={}, fp=io.BytesIO()
        )
        adapter = DiscordWebhookAdapter(webhook_url="https://discord.com/api/webhooks/test/dummy")
        result = adapter.notify_milestone("Title", "Desc", sync=True)
        self.assertFalse(result)

    @patch("urllib.request.urlopen")
    def test_url_error_does_not_raise(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError(reason="Connection refused")
        adapter = DiscordWebhookAdapter(webhook_url="https://discord.com/api/webhooks/test/dummy")
        result = adapter.notify_alarm("CODE", "Title", "Reason", sync=True)
        self.assertFalse(result)

    @patch.dict(os.environ, {"DISCORD_WEBHOOK_URL": "https://discord.com/env-webhook"})
    def test_resolve_webhook_url_from_env(self):
        url = resolve_webhook_url()
        self.assertEqual(url, "https://discord.com/env-webhook")

    def test_get_notifier_returns_null_when_no_webhook(self):
        with patch("runtime.notifier.resolve_webhook_url", return_value=None):
            notifier = get_notifier()
            self.assertIsInstance(notifier, NullNotifier)

    def test_get_notifier_returns_adapter_when_configured(self):
        with patch("runtime.notifier.resolve_webhook_url", return_value="https://discord.com/test"):
            notifier = get_notifier()
            self.assertIsInstance(notifier, DiscordWebhookAdapter)

    @patch("runtime.notifier._safe_print")
    def test_send_test_notifications_dry_run_success(self, _mock_print):
        result = send_test_notifications(
            webhook_url="https://discord.com/test",
            test_type="all",
            live=False,
        )
        self.assertTrue(result)

    @patch("runtime.notifier._safe_print")
    def test_send_test_notifications_unconfigured_live_fails(self, _mock_print):
        with patch("runtime.notifier.resolve_webhook_url", return_value=None):
            result = send_test_notifications(webhook_url="", profile=None, live=True)
            self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
