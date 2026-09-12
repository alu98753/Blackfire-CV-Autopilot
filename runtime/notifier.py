"""Notification infrastructure implementing Hexagonal NotificationPort and Discord Webhook Adapter."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Mapping

DEFAULT_TIMEOUT_SECONDS: float = 3.0
DISCORD_COLOR_MILESTONE: int = 0x2ECC71  # Emerald Green
DISCORD_COLOR_ALARM: int = 0xE74C3C      # Bright Red


class NotificationPort(ABC):
    """Abstract interface defining system-to-operator notification capabilities."""

    @abstractmethod
    def notify_milestone(
        self,
        title: str,
        description: str,
        fields: Mapping[str, Any] | None = None,
        sync: bool = False,
    ) -> bool:
        """Send an AUTOMATION_HEALTHY milestone notification."""

    @abstractmethod
    def notify_alarm(
        self,
        code: str,
        title: str,
        reason: str,
        details: Mapping[str, Any] | None = None,
        sync: bool = False,
    ) -> bool:
        """Send an OPERATOR_ACTION_REQUIRED unrecoverable failure alarm."""


class NullNotifier(NotificationPort):
    """No-op notifier used when notifications are disabled or unconfigured."""

    def notify_milestone(
        self,
        title: str,
        description: str,
        fields: Mapping[str, Any] | None = None,
        sync: bool = False,
    ) -> bool:
        logging.debug("[NullNotifier] Milestone suppressed: %s", title)
        return False

    def notify_alarm(
        self,
        code: str,
        title: str,
        reason: str,
        details: Mapping[str, Any] | None = None,
        sync: bool = False,
    ) -> bool:
        logging.debug("[NullNotifier] Alarm suppressed (%s): %s", code, title)
        return False


class DiscordWebhookAdapter(NotificationPort):
    """Outbound adapter delivering domain notifications to Discord via webhook."""

    def __init__(self, webhook_url: str, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self.webhook_url = webhook_url.strip()
        self.timeout_seconds = max(1.0, float(timeout_seconds))

    def notify_milestone(
        self,
        title: str,
        description: str,
        fields: Mapping[str, Any] | None = None,
        sync: bool = False,
    ) -> bool:
        embed = self._build_embed(
            title=f"✅ {title}",
            description=description,
            color=DISCORD_COLOR_MILESTONE,
            fields=fields,
            footer_text="Blackfire Crusade • Automation Healthy",
        )
        return self._dispatch(embed, sync=sync)

    def notify_alarm(
        self,
        code: str,
        title: str,
        reason: str,
        details: Mapping[str, Any] | None = None,
        sync: bool = False,
    ) -> bool:
        merged_details = dict(details or {})
        merged_details["Alarm Code"] = code
        merged_details["Reason"] = reason

        embed = self._build_embed(
            title=f"🚨 {title}",
            description="Automatic recovery exhausted. Manual intervention required.",
            color=DISCORD_COLOR_ALARM,
            fields=merged_details,
            footer_text="Blackfire Crusade • Operator Action Required",
        )
        return self._dispatch(embed, sync=sync)

    def _build_embed(
        self,
        title: str,
        description: str,
        color: int,
        fields: Mapping[str, Any] | None,
        footer_text: str,
    ) -> dict[str, Any]:
        embed_fields: list[dict[str, Any]] = []
        if fields:
            for k, v in fields.items():
                val_str = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
                embed_fields.append({"name": str(k), "value": val_str, "inline": False})

        return {
            "title": title,
            "description": description,
            "color": color,
            "fields": embed_fields,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "footer": {"text": footer_text},
        }

    def _dispatch(self, embed: dict[str, Any], sync: bool) -> bool:
        payload = {"embeds": [embed]}
        if sync:
            return self._post_payload(payload)

        worker = threading.Thread(
            target=self._post_payload,
            args=(payload,),
            daemon=True,
            name="DiscordNotificationThread",
        )
        worker.start()
        return True

    def _post_payload(self, payload: dict[str, Any]) -> bool:
        if not self.webhook_url:
            logging.warning("[DiscordNotifier] Webhook URL is empty; skipping notification.")
            return False

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.webhook_url,
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
                if status in (200, 204):
                    logging.info("[DiscordNotifier] Notification delivered successfully (status: %d).", status)
                    return True
                logging.warning("[DiscordNotifier] Unexpected response status: %d", status)
                return False
        except urllib.error.HTTPError as ex:
            logging.warning("[DiscordNotifier] HTTP error delivering notification (%d): %s", ex.code, ex.reason)
            return False
        except urllib.error.URLError as ex:
            logging.warning("[DiscordNotifier] Network error delivering notification: %s", ex.reason)
            return False
        except Exception as ex:
            logging.warning("[DiscordNotifier] Unexpected failure delivering notification: %s", ex)
            return False


def resolve_webhook_url(profile: str | None = None) -> str | None:
    """Resolve webhook URL with precedence: ENV > user_data/<profile>/config.toml > defaults.toml."""
    env_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if env_url:
        return env_url

    if profile:
        try:
            from config import set_active_profile
            set_active_profile(profile)
        except Exception:
            pass

    try:
        from config import get_defaults_config
        cfg = get_defaults_config()
        discord_cfg = cfg.get("notification", {}).get("discord", {})
        if discord_cfg.get("enabled", True):
            url = discord_cfg.get("webhook_url", "").strip()
            if url:
                return url
    except Exception:
        pass

    return None


def get_notifier(profile: str | None = None) -> NotificationPort:
    """Factory creating an active DiscordWebhookAdapter if configured, else NullNotifier."""
    url = resolve_webhook_url(profile=profile)
    if url:
        return DiscordWebhookAdapter(webhook_url=url)
    return NullNotifier()


def build_milestone_payload(
    title: str,
    description: str,
    fields: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Pure function constructing an AUTOMATION_HEALTHY Discord embed payload."""
    embed_fields: list[dict[str, Any]] = []
    if fields:
        for k, v in fields.items():
            val_str = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
            embed_fields.append({"name": str(k), "value": val_str, "inline": False})

    return {
        "embeds": [
            {
                "title": f"✅ {title}",
                "description": description,
                "color": DISCORD_COLOR_MILESTONE,
                "fields": embed_fields,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "footer": {"text": "Blackfire Crusade • Automation Healthy"},
            }
        ]
    }


def build_alarm_payload(
    code: str,
    title: str,
    reason: str,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Pure function constructing an OPERATOR_ACTION_REQUIRED Discord embed payload."""
    merged_details = dict(details or {})
    merged_details["Alarm Code"] = code
    merged_details["Reason"] = reason

    embed_fields: list[dict[str, Any]] = []
    for k, v in merged_details.items():
        val_str = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
        embed_fields.append({"name": str(k), "value": val_str, "inline": False})

    return {
        "embeds": [
            {
                "title": f"🚨 {title}",
                "description": "Automatic recovery exhausted. Manual intervention required.",
                "color": DISCORD_COLOR_ALARM,
                "fields": embed_fields,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "footer": {"text": "Blackfire Crusade • Operator Action Required"},
            }
        ]
    }


def send_test_notifications(
    webhook_url: str | None = None,
    profile: str | None = None,
    test_type: str = "all",
    live: bool = False,
) -> bool:
    """
    Execute test notification with strict Dry-Run vs Live isolation.
    - When live=False: print the formatted JSON payload preview directly to stdout without network I/O.
    - When live=True: requires a configured webhook URL and performs synchronous HTTP POST.
    """
    url = (webhook_url or "").strip() or resolve_webhook_url(profile=profile)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 讀取真實 DailyManager 狀態作為 payload 資料源 (若存在)
    accepted_quests = ["測試任務 A (地精王國)", "測試任務 B (荒漠古城)"]
    town_subflows_summary = "chest(✓), hero_draw(✓), blood_altar(✓), jewelry_workshop(✓), bulletin_board(✓)"
    try:
        from utils.daily_manager import DailyManager
        dm = DailyManager(profile=profile)
        bb_quests = dm.status.get("subflows", {}).get("bulletin_board", {}).get("accepted_quests", [])
        if bb_quests:
            accepted_quests = bb_quests
        sf_statuses = []
        for sf in ["chest", "hero_draw", "blood_altar", "jewelry_workshop", "bulletin_board"]:
            done = dm.is_subflow_completed(sf)
            sf_statuses.append(f"{sf}({'✓' if done else '✗'})")
        town_subflows_summary = ", ".join(sf_statuses)
    except Exception:
        pass

    targets: list[tuple[str, dict[str, Any]]] = []

    if test_type in ("all", "milestone", "milestone1"):
        payload = build_milestone_payload(
            title="Daily Claim Phase Completed",
            description="All town daily claim subflows completed; bulletin board bounty quests accepted.",
            fields={
                "Timestamp": now_str,
                "Profile": profile or "default",
                "Quests Accepted": accepted_quests,
                "Town Subflows": town_subflows_summary,
            },
        )
        targets.append(("Milestone 1: Daily Claim Phase Completed", payload))

    if test_type in ("all", "milestone", "milestone2"):
        payload = build_milestone_payload(
            title="Bounty Quests Cleared",
            description="All accepted bounty quests completed. Bot transitioning to steady-state mode.",
            fields={
                "Timestamp": now_str,
                "Profile": profile or "default",
                "Cleared Quests Count": len(accepted_quests),
                "Cleared Quests": accepted_quests,
                "Next Target": "Tier 4 Loop (mix)",
            },
        )
        targets.append(("Milestone 2: Bounty Quests Cleared", payload))

    if test_type in ("all", "alarm"):
        payload = build_alarm_payload(
            code="SUPERVISOR_CRASH_LOOP_EXCEEDED",
            title="Supervisor Crash Loop Exceeded",
            reason="Supervisor exceeded 5 restarts within sliding window (600s).",
            details={
                "Timestamp": now_str,
                "Profile": profile or "default",
                "Restarts in Window": "5 / 5",
                "Window Duration": "10.0 minutes",
            },
        )
        targets.append(("Alarm: Supervisor Crash Loop Exceeded", payload))

    if test_type in ("all", "deadline"):
        payload = build_alarm_payload(
            code="DAILY_CLAIM_DEADLINE_EXCEEDED",
            title="Daily Claim Deadline Exceeded",
            reason="Daily claim phase not completed within 30 minutes after 08:05 reset.",
            details={
                "Timestamp": now_str,
                "Profile": profile or "default",
                "Pending Subflows": "jewelry_workshop, bulletin_board",
            },
        )
        targets.append(("Alarm: Daily Claim Deadline Exceeded", payload))

    if not live:
        print("\n" + "=" * 65)
        print("🔍 [DRY-RUN PREVIEW] Discord Webhook Notification Payload (No Network Sent)")
        print("💡 Hint: Pass '--live' to perform actual HTTP POST to Discord.")
        print(f"📡 Webhook URL Status: {'Configured (' + url[:30] + '...)' if url else 'NOT CONFIGURED'}")
        print("=" * 65)
        for label, payload in targets:
            print(f"\n--- [{label}] ---")
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        print("=" * 65 + "\n")
        return True

    # --- LIVE SENDING MODE ---
    if not url:
        print("\n❌ [ERROR] DISCORD_WEBHOOK_URL is required for live send.")
        print("   Please set DISCORD_WEBHOOK_URL in environment or configure it in TOML.\n")
        return False

    print("\n" + "=" * 65)
    print(f"🚀 [LIVE SEND] Dispatching {len(targets)} notification(s) to Discord...")
    print(f"📡 Webhook URL: {url[:35]}...")
    print("=" * 65)

    notifier = DiscordWebhookAdapter(webhook_url=url)
    all_success = True
    for label, payload in targets:
        print(f"[*] Posting [{label}]...")
        ok = notifier._post_payload(payload)
        status_text = "✅ SUCCESS" if ok else "❌ FAILED"
        print(f"    Delivery: {status_text}")
        if not ok:
            all_success = False

    print("=" * 65 + "\n")
    return all_success


def main() -> int:
    parser = argparse.ArgumentParser(description="Discord Webhook Notification Diagnostic Tool.")
    parser.add_argument("--url", type=str, default=None, help="Explicit Discord Webhook URL for one-off testing")
    parser.add_argument("--profile", type=str, default=None, help="Profile name to resolve webhook config")
    parser.add_argument(
        "--type",
        choices=["all", "milestone", "milestone1", "milestone2", "alarm", "deadline"],
        default="all",
        help="Notification type to test (default: all)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        default=False,
        help="Perform real HTTP POST to Discord (default: Dry-Run preview only)",
    )
    args = parser.parse_args()

    ok = send_test_notifications(
        webhook_url=args.url,
        profile=args.profile,
        test_type=args.type,
        live=args.live,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
