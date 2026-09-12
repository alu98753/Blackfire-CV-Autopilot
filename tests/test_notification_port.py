"""Unit tests for NotificationPort and DiscordWebhookAdapter."""

from __future__ import annotations

import io
import json
import os
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

from ports.notification_port import (
    DISCORD_COLOR_ALARM,
    DISCORD_COLOR_MILESTONE,
    DeleteResult,
    NotificationPort,
    NotificationResult,
    NullNotifier,
)
from runtime.discord_webhook_adapter import DiscordWebhookAdapter, inject_query_param
from runtime.notifier_factory import create_notification_port, resolve_webhook_url
from tools.notifier_cli import send_test_notifications


class TestNotificationPort(unittest.TestCase):
    """Verify behavior of NotificationPort implementations and webhook delivery."""

    def test_null_notifier_is_safe_noop(self):
        notifier = NullNotifier()
        self.assertIsInstance(notifier, NotificationPort)
        self.assertFalse(notifier.notify_milestone("Test Title", "Test Desc"))
        self.assertFalse(notifier.notify_alarm("ERR_CODE", "Test Title", "Test Reason"))
        del_res = notifier.delete_message("12345")
        self.assertFalse(del_res)
        self.assertEqual(del_res.error, "NullNotifier")

    def test_inject_query_param(self):
        self.assertEqual(
            inject_query_param("https://discord.com/api/webhooks/123", "wait", "true"),
            "https://discord.com/api/webhooks/123?wait=true",
        )
        self.assertEqual(
            inject_query_param("https://discord.com/api/webhooks/123?thread_id=456", "wait", "true"),
            "https://discord.com/api/webhooks/123?thread_id=456&wait=true",
        )
        self.assertEqual(
            inject_query_param("https://discord.com/api/webhooks/123?wait=false", "wait", "true"),
            "https://discord.com/api/webhooks/123?wait=true",
        )

    @patch("urllib.request.urlopen")
    def test_discord_webhook_adapter_milestone_returns_message_id(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({"id": "999888777"}).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        adapter = DiscordWebhookAdapter(webhook_url="https://discord.com/api/webhooks/test/dummy")
        result = adapter.notify_milestone("Title", "Desc", sync=True)
        self.assertTrue(result)
        self.assertEqual(result.external_message_id, "999888777")

    @patch("urllib.request.urlopen")
    def test_discord_webhook_delete_message_success_204(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        adapter = DiscordWebhookAdapter(webhook_url="https://discord.com/api/webhooks/123/abc")
        result = adapter.delete_message("msg_456")
        self.assertTrue(result)
        self.assertEqual(result.status_code, 204)
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.full_url, "https://discord.com/api/webhooks/123/abc/messages/msg_456")
        self.assertEqual(req.get_method(), "DELETE")

    @patch("urllib.request.urlopen")
    def test_discord_webhook_delete_message_404_treated_as_success(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="http://test", code=404, msg="Not Found", hdrs={}, fp=io.BytesIO(b'{"message": "Unknown Message"}')
        )
        adapter = DiscordWebhookAdapter(webhook_url="https://discord.com/api/webhooks/123/abc")
        result = adapter.delete_message("msg_456")
        self.assertTrue(result)
        self.assertEqual(result.status_code, 404)

    @patch("urllib.request.urlopen")
    def test_discord_webhook_delete_message_429_rate_limited(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="http://test", code=429, msg="Too Many Requests",
            hdrs={"Retry-After": "12.5"},
            fp=io.BytesIO(b'{"retry_after": 12.5, "message": "Rate limited"}'),
        )
        adapter = DiscordWebhookAdapter(webhook_url="https://discord.com/api/webhooks/123/abc")
        result = adapter.delete_message("msg_456")
        self.assertFalse(result)
        self.assertEqual(result.status_code, 429)
        self.assertAlmostEqual(result.retry_after_seconds, 12.5)

    @patch("urllib.request.urlopen")
    def test_discord_webhook_delete_message_500_failure(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="http://test", code=500, msg="Internal Server Error", hdrs={}, fp=io.BytesIO()
        )
        adapter = DiscordWebhookAdapter(webhook_url="https://discord.com/api/webhooks/123/abc")
        result = adapter.delete_message("msg_456")
        self.assertFalse(result)
        self.assertEqual(result.status_code, 500)

    @patch("urllib.request.urlopen")
    def test_discord_webhook_delete_message_preserves_query_params(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        adapter = DiscordWebhookAdapter(webhook_url="https://discord.com/api/webhooks/123/abc?thread_id=777")
        result = adapter.delete_message("msg_456")
        self.assertTrue(result)
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.full_url, "https://discord.com/api/webhooks/123/abc/messages/msg_456?thread_id=777")

    @patch("urllib.request.urlopen")
    def test_discord_webhook_adapter_milestone_payload(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({"id": "1122334455"}).encode("utf-8")
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
        self.assertEqual(result.external_message_id, "1122334455")
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.full_url, "https://discord.com/api/webhooks/test/dummy?wait=true")
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
        mock_response.read.return_value = json.dumps({"id": "5544332211"}).encode("utf-8")
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
        self.assertEqual(result.external_message_id, "5544332211")
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

    @patch("urllib.request.urlopen")
    def test_wait_true_with_204_returns_failure(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        adapter = DiscordWebhookAdapter(webhook_url="https://discord.com/api/webhooks/test/dummy")
        result = adapter.notify_milestone("Title", "Desc", sync=True)
        self.assertFalse(result)
        self.assertIsNone(result.external_message_id)
        self.assertIn("Expected HTTP 200 with wait=true, got 204", str(result.error))

    @patch("urllib.request.urlopen")
    def test_wait_true_with_200_missing_id_returns_failure(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"type": 0, "content": "hello"}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        adapter = DiscordWebhookAdapter(webhook_url="https://discord.com/api/webhooks/test/dummy")
        result = adapter.notify_milestone("Title", "Desc", sync=True)
        self.assertFalse(result)
        self.assertIsNone(result.external_message_id)
        self.assertEqual(result.error, "Discord response missing message id")

    @patch("urllib.request.urlopen")
    def test_wait_true_with_malformed_json_returns_failure(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'not valid json <<<'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        adapter = DiscordWebhookAdapter(webhook_url="https://discord.com/api/webhooks/test/dummy")
        result = adapter.notify_milestone("Title", "Desc", sync=True)
        self.assertFalse(result)
        self.assertIsNone(result.external_message_id)
        self.assertIn("Invalid Discord response body", str(result.error))

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

    def test_get_notification_webhook_url_from_defaults_and_profile(self):
        from config import get_notification_webhook_url
        with patch.dict(os.environ, {}, clear=True):
            with patch("config.get_defaults_config", return_value={"notification": {"discord": {"webhook_url": "https://discord.com/default-url"}}}):
                self.assertEqual(get_notification_webhook_url(None), "https://discord.com/default-url")
                # Profile override
                with patch("pathlib.Path.exists", return_value=True):
                    with patch("config.TomlConfigManager.snapshot", return_value={"notification": {"discord": {"webhook_url": "https://discord.com/profile-url"}}}):
                        self.assertEqual(get_notification_webhook_url("custom_prof"), "https://discord.com/profile-url")

    def test_resolve_webhook_url_from_toml_when_env_empty(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("config.get_notification_webhook_url", return_value="https://discord.com/toml-webhook"):
                url = resolve_webhook_url(profile="native")
                self.assertEqual(url, "https://discord.com/toml-webhook")

    def test_create_notification_port_returns_null_when_no_webhook(self):
        with patch("runtime.notifier_factory.resolve_webhook_url", return_value=None):
            notifier = create_notification_port()
            self.assertIsInstance(notifier, NullNotifier)

    def test_create_notification_port_returns_adapter_when_configured(self):
        with patch("runtime.notifier_factory.resolve_webhook_url", return_value="https://discord.com/test"):
            notifier = create_notification_port()
            self.assertIsInstance(notifier, DiscordWebhookAdapter)

    def test_json_notification_history_store_roundtrip(self):
        import tempfile
        from runtime.json_notification_history_store import JsonNotificationHistoryStore
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, "history.json")
            store = JsonNotificationHistoryStore(history_file_path=fpath)
            loaded = store.load_history()
            self.assertEqual(loaded.get("dispatched_messages"), [])
            loaded["last_reconciled_date"] = "2026-09-12"
            store.save_history(loaded)
            reloaded = store.load_history()
            self.assertEqual(reloaded.get("last_reconciled_date"), "2026-09-12")

    def test_json_notification_history_store_atomic_replace_and_no_tmp_leak(self):
        import tempfile
        from runtime.json_notification_history_store import JsonNotificationHistoryStore
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, "history.json")
            store = JsonNotificationHistoryStore(history_file_path=fpath)
            data = {"last_milestone1_date": "2026-09-12", "dispatched_messages": []}
            store.save_history(data)
            self.assertTrue(os.path.exists(fpath))
            self.assertFalse(os.path.exists(f"{fpath}.tmp"))
            with open(fpath, "r", encoding="utf-8") as f:
                saved = json.load(f)
            self.assertEqual(saved["last_milestone1_date"], "2026-09-12")

    def test_daily_reconciliation_evicts_missing_and_empty_id_entries(self):
        from states.daily_reconciliation import DailyReconciliationService
        from ports.notification_history_port import InMemoryNotificationHistoryStore
        store = InMemoryNotificationHistoryStore()
        history = {
            "dispatched_messages": [
                {"id": "", "date": "2026-09-11"},
                {"date": "2026-09-11"},
                {"id": "valid_123", "date": "2026-09-12"},
            ]
        }
        store.save_history(history)
        service = DailyReconciliationService(
            notification_port=NullNotifier(),
            history_store=store,
        )
        service._evict_message_id(history, "")
        remaining = history["dispatched_messages"]
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["id"], "valid_123")

    @patch("tools.notifier_cli._safe_print")
    def test_send_test_notifications_dry_run_success(self, _mock_print):
        result = send_test_notifications(
            webhook_url="https://discord.com/test",
            test_type="all",
            live=False,
        )
        self.assertTrue(result)

    @patch("tools.notifier_cli._safe_print")
    def test_send_test_notifications_unconfigured_live_fails(self, _mock_print):
        with patch("tools.notifier_cli.resolve_webhook_url", return_value=None):
            result = send_test_notifications(webhook_url="", profile=None, live=True)
            self.assertFalse(result)

    @patch("tools.notifier_cli._safe_print")
    def test_send_test_notifications_delete_after_requires_live(self, mock_print):
        res = send_test_notifications(
            webhook_url="https://discord.com/test",
            live=False,
            delete_after_seconds=5.0,
        )
        self.assertFalse(res)
        self.assertTrue(any("--delete-after" in str(c) for c in mock_print.call_args_list))

    @patch("tools.notifier_cli._safe_print")
    def test_send_test_notifications_test_reconcile_requires_live(self, mock_print):
        res = send_test_notifications(
            webhook_url="https://discord.com/test",
            live=False,
            test_reconcile=True,
        )
        self.assertFalse(res)
        self.assertTrue(any("--test-reconcile" in str(c) for c in mock_print.call_args_list))

    @patch("time.sleep")
    @patch("tools.notifier_cli._safe_print")
    def test_run_live_deletion_verification_success(self, _mock_print, mock_sleep):
        from tools.notifier_cli import _run_live_deletion_verification
        adapter = MagicMock()
        adapter.delete_message.side_effect = [
            DeleteResult(success=True, status_code=204),
            DeleteResult(success=True, status_code=404),
        ]
        res = _run_live_deletion_verification(adapter, "msg_123", delete_after_seconds=3.0)
        self.assertTrue(res)
        self.assertEqual(adapter.delete_message.call_count, 2)
        adapter.delete_message.assert_called_with("msg_123")
        self.assertEqual(mock_sleep.call_count, 3)

    @patch("time.sleep")
    @patch("tools.notifier_cli._safe_print")
    def test_run_live_reconcile_verification_success(self, _mock_print, _mock_sleep):
        from tools.notifier_cli import _run_live_reconcile_verification
        with patch.object(DiscordWebhookAdapter, "notify_milestone") as mock_notify, \
             patch.object(DiscordWebhookAdapter, "delete_message") as mock_del:
            mock_notify.return_value = NotificationResult(success=True, external_message_id="discord_msg_888")
            mock_del.side_effect = [
                DeleteResult(success=True, status_code=204),
                DeleteResult(success=True, status_code=404),
            ]
            res = _run_live_reconcile_verification(
                webhook_url="https://discord.com/api/webhooks/test/dummy",
                profile="test_profile",
                language="zh_TW",
                delete_after_seconds=0.0,
            )
            self.assertTrue(res)
            mock_notify.assert_called_once()
            self.assertEqual(mock_del.call_count, 2)


    def test_cli_arguments_test_notify_options(self):
        from cli.arguments import parse_arguments
        with patch("sys.argv", ["main.py", "--test-notify", "milestone1", "--live", "--delete-after", "5.0", "--test-reconcile"]):
            args = parse_arguments()
            self.assertEqual(args.test_notify, "milestone1")
            self.assertTrue(args.live)
            self.assertEqual(args.delete_after, 5.0)
            self.assertTrue(args.test_reconcile)


if __name__ == "__main__":
    unittest.main()

