"""Coordinator for daily pipeline milestone notifications and deadline alarms.

Follows Greenfield-lite v1:
- Owned by GameStateMachine (similar to BattleSession / StaminaRetreatRecovery).
- Queries DailyManager for pure state facts without polluting daily_status.json.
- Tracks notification idempotency across restarts in profile-isolated runtime storage.
- Dispatches milestones and alarms via NotificationPort with safe exception suppression.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, time as dtime, timedelta
from typing import Any

from config import USER_DATA_DIR
from runtime.incident_journal import normalize_profile
from runtime.notifier import NotificationPort, NullNotifier


class DailyPipelineNotifier:
    """Coordinates Daily Pipeline Milestone 1, Milestone 2, and Deadline Alarm notifications."""

    def __init__(
        self,
        notification_port: NotificationPort | None = None,
        daily_manager: Any | None = None,
        profile: str | None = None,
        deadline_minutes: int = 30,
        history_file_path: str | None = None,
    ) -> None:
        self.notification_port: NotificationPort = notification_port or NullNotifier()
        self.daily_manager = daily_manager
        self.profile = normalize_profile(profile)
        self.deadline_minutes = max(1, int(deadline_minutes))

        if history_file_path:
            self.history_file = history_file_path
        else:
            runtime_dir = os.path.join(USER_DATA_DIR, self.profile, "runtime")
            self.history_file = os.path.join(runtime_dir, "notification_history.json")

        self.history: dict[str, str] = self._load_history()

    def _load_history(self) -> dict[str, str]:
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception as e:
                logging.warning("[DailyPipelineNotifier] Failed to load history file (%s): %s", self.history_file, e)
        return {
            "last_milestone1_date": "",
            "last_milestone2_date": "",
            "last_deadline_alarm_date": "",
        }

    def _save_history(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.warning("[DailyPipelineNotifier] Failed to save history file (%s): %s", self.history_file, e)

    def get_current_reset_tag(self, now_dt: datetime | None = None) -> str:
        """Resolve current 08:05 cycle tag (YYYY-MM-DD) via daily_manager or fallback."""
        if self.daily_manager and hasattr(self.daily_manager, "get_today_reset_tag"):
            return self.daily_manager.get_today_reset_tag(now_dt)
        now_dt = now_dt or datetime.now()
        reset_time = dtime(8, 5)
        if now_dt.time() < reset_time:
            return (now_dt.date() - timedelta(days=1)).strftime("%Y-%m-%d")
        return now_dt.date().strftime("%Y-%m-%d")

    def is_milestone_eligible(self, milestone_key: str, now_dt: datetime | None = None) -> bool:
        """Verify whether the milestone has already been dispatched for the current reset cycle."""
        current_tag = self.get_current_reset_tag(now_dt)
        return self.history.get(f"last_{milestone_key}_date") != current_tag

    def record_milestone_notified(self, milestone_key: str, now_dt: datetime | None = None) -> None:
        """Persist notified record to guarantee idempotency across process restarts."""
        current_tag = self.get_current_reset_tag(now_dt)
        self.history[f"last_{milestone_key}_date"] = current_tag
        self._save_history()

    def on_tier1_subflow_completed(self, subflow_key: str = "bulletin_board", now_dt: datetime | None = None) -> bool:
        """
        Evaluate Tier 1 completion upon completing a subflow.
        If all Tier 1 subflows are completed and milestone1 is eligible, dispatch Milestone 1.
        """
        if not self.daily_manager or not hasattr(self.daily_manager, "is_tier1_daily_claim_completed"):
            return False

        if not self.daily_manager.is_tier1_daily_claim_completed():
            return False

        if not self.is_milestone_eligible("milestone1", now_dt):
            return False

        # Gather accepted quests and subflow statuses
        accepted_quests = []
        if hasattr(self.daily_manager, "status"):
            accepted_quests = self.daily_manager.status.get("subflows", {}).get(
                "bulletin_board", {}
            ).get("accepted_quests", [])

        sf_statuses = []
        for sf in ["chest", "hero_draw", "blood_altar", "jewelry_workshop", "bulletin_board"]:
            done = self.daily_manager.is_subflow_completed(sf) if hasattr(self.daily_manager, "is_subflow_completed") else False
            sf_statuses.append(f"{sf}({'✓' if done else '✗'})")

        now_str = (now_dt or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
        res = self.notification_port.notify_milestone(
            title="Daily Claim Phase Completed",
            description="All town daily claim subflows completed; bulletin board bounty quests accepted.",
            fields={
                "Timestamp": now_str,
                "Profile": self.profile,
                "Quests Accepted": accepted_quests,
                "Town Subflows": ", ".join(sf_statuses),
            },
        )
        self.record_milestone_notified("milestone1", now_dt)
        logging.info("🔔 [DailyPipelineNotifier] 已發送 Milestone 1 (Daily Claim Phase Completed) 通知！")
        return res

    def on_bounty_quests_cleared(self, fallback_mode: str = "Tier 4 Loop (mix)", now_dt: datetime | None = None) -> bool:
        """
        Dispatch Milestone 2 when all bounty quests have been cleared and state machine switches to Tier 4.
        """
        if not self.is_milestone_eligible("milestone2", now_dt):
            return False

        now_str = (now_dt or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
        res = self.notification_port.notify_milestone(
            title="Bounty Quests Cleared",
            description="All accepted bounty quests completed. Bot transitioning to steady-state mode.",
            fields={
                "Timestamp": now_str,
                "Profile": self.profile,
                "Status": "All accepted quests completed",
                "Next Target": fallback_mode,
            },
        )
        self.record_milestone_notified("milestone2", now_dt)
        logging.info("🔔 [DailyPipelineNotifier] 已發送 Milestone 2 (Bounty Quests Cleared) 通知！")
        return res

    def check_daily_claim_deadline(self, current_state: str = "UNKNOWN", now_dt: datetime | None = None) -> bool:
        """
        Periodically check if 08:05 reset deadline (default 30m, 08:35) has been exceeded
        while Tier 1 daily claims remain incomplete.
        """
        if not self.daily_manager or not hasattr(self.daily_manager, "is_tier1_daily_claim_completed"):
            return False

        if self.daily_manager.is_tier1_daily_claim_completed():
            return False

        now_dt = now_dt or datetime.now()
        reset_hour = getattr(self.daily_manager, "reset_hour", 8)
        reset_minute = getattr(self.daily_manager, "reset_minute", 5)
        reset_time = dtime(reset_hour, reset_minute)

        if now_dt.time() < reset_time:
            last_reset_dt = datetime.combine(now_dt.date() - timedelta(days=1), reset_time)
        else:
            last_reset_dt = datetime.combine(now_dt.date(), reset_time)

        deadline_dt = last_reset_dt + timedelta(minutes=self.deadline_minutes)

        if now_dt < deadline_dt:
            return False

        if not self.is_milestone_eligible("deadline_alarm", now_dt):
            return False

        pending_subflows = []
        if hasattr(self.daily_manager, "get_pending_tier1_subflows"):
            pending_subflows = self.daily_manager.get_pending_tier1_subflows()

        now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
        res = self.notification_port.notify_alarm(
            code="DAILY_CLAIM_DEADLINE_EXCEEDED",
            title="Daily Claim Deadline Exceeded",
            reason=f"Daily claim phase not completed within {self.deadline_minutes} minutes after 08:05 reset.",
            details={
                "Timestamp": now_str,
                "Profile": self.profile,
                "Pending Subflows": ", ".join(pending_subflows) or "Unknown",
                "Current State": current_state,
            },
        )
        self.record_milestone_notified("deadline_alarm", now_dt)
        logging.error("🚨 [DailyPipelineNotifier] 已觸發 DAILY_CLAIM_DEADLINE_EXCEEDED 警報通知！")
        return res
