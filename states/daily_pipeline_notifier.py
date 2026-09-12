"""Coordinator for daily pipeline milestone notifications and deadline alarms.

Follows Greenfield-lite v1:
- Owned by GameStateMachine (similar to BattleSession / StaminaRetreatRecovery).
- Queries DailyManager for pure state facts without polluting daily_status.json.
- Tracks notification idempotency across restarts in profile-isolated runtime storage.
- Dispatches milestones and alarms via NotificationPort with safe exception suppression.
- Performs Desired-State Reconciliation of expired webhook messages at 07:00 Asia/Taipei.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, time as dtime, timedelta, timezone
from typing import Any

from config import USER_DATA_DIR
from runtime.incident_journal import normalize_profile
from runtime.notifier import NotificationPort, NullNotifier

DEFAULT_RECONCILE_CHECK_INTERVAL_SECONDS: float = 5.0
DEFAULT_RECONCILE_COOLDOWN_SECONDS: float = 60.0
EARLIEST_RECONCILE_HOUR: int = 7
EARLIEST_RECONCILE_MINUTE: int = 0

try:
    from zoneinfo import ZoneInfo
    TAIPEI_TZ = ZoneInfo("Asia/Taipei")
except Exception:
    TAIPEI_TZ = timezone(timedelta(hours=8), name="Asia/Taipei")


def resolve_business_dt(now_dt: datetime | None = None) -> datetime:
    """Resolve current business datetime in Asia/Taipei timezone.

    Guarantees deterministic date calculation independent of host OS timezone.
    """
    if now_dt is None:
        return datetime.now(TAIPEI_TZ)
    if now_dt.tzinfo is None:
        return now_dt.replace(tzinfo=TAIPEI_TZ)
    return now_dt.astimezone(TAIPEI_TZ)


class DailyPipelineNotifier:
    """Coordinates Daily Pipeline Milestone 1, Milestone 2, and Deadline Alarm notifications."""

    def __init__(
        self,
        notification_port: NotificationPort | None = None,
        daily_manager: Any | None = None,
        profile: str | None = None,
        deadline_minutes: int = 30,
        history_file_path: str | None = None,
        language: str | None = None,
        check_interval_seconds: float = DEFAULT_RECONCILE_CHECK_INTERVAL_SECONDS,
    ) -> None:
        self.notification_port: NotificationPort = notification_port or NullNotifier()
        self.daily_manager = daily_manager
        self.profile = normalize_profile(profile)
        self.deadline_minutes = max(1, int(deadline_minutes))
        self.check_interval_seconds = max(0.5, float(check_interval_seconds))
        self._next_reconcile_check_ts = 0.0

        if language is not None:
            from runtime.notification_i18n import normalize_language
            self.language = normalize_language(language)
        else:
            from config import get_notification_language
            self.language = get_notification_language(profile=self.profile)

        if history_file_path:
            self.history_file = history_file_path
        else:
            runtime_dir = os.path.join(USER_DATA_DIR, self.profile, "runtime")
            self.history_file = os.path.join(runtime_dir, "notification_history.json")

        self.history: dict[str, Any] = self._load_history()

    def _load_history(self) -> dict[str, Any]:
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        if "dispatched_messages" not in data or not isinstance(data["dispatched_messages"], list):
                            data["dispatched_messages"] = []
                        return data
            except Exception as e:
                logging.warning("[DailyPipelineNotifier] Failed to load history file (%s): %s", self.history_file, e)
        return {
            "last_milestone1_date": "",
            "last_milestone2_date": "",
            "last_deadline_alarm_date": "",
            "last_reconciled_date": "",
            "dispatched_messages": [],
        }

    def _save_history(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.warning("[DailyPipelineNotifier] Failed to save history file (%s): %s", self.history_file, e)

    def get_today_date_tag(self, now_dt: datetime | None = None) -> str:
        """Resolve today's calendar date tag (YYYY-MM-DD) in Asia/Taipei."""
        return resolve_business_dt(now_dt).strftime("%Y-%m-%d")

    def get_current_reset_tag(self, now_dt: datetime | None = None) -> str:
        """Resolve current 08:05 cycle tag (YYYY-MM-DD) via daily_manager or fallback."""
        if self.daily_manager and hasattr(self.daily_manager, "get_today_reset_tag"):
            return self.daily_manager.get_today_reset_tag(now_dt)
        now_dt = resolve_business_dt(now_dt)
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

    def track_dispatched_message(
        self,
        message_id: str,
        tag: str = "",
        now_dt: datetime | None = None,
    ) -> None:
        """Track dispatched webhook message ID for future 07:00 reconciliation."""
        if not message_id:
            return
        msg_date_tag = self.get_today_date_tag(now_dt)
        if "dispatched_messages" not in self.history or not isinstance(self.history["dispatched_messages"], list):
            self.history["dispatched_messages"] = []

        existing = [m for m in self.history["dispatched_messages"] if m.get("id") == message_id]
        if not existing:
            self.history["dispatched_messages"].append({
                "id": str(message_id).strip(),
                "date": msg_date_tag,
                "tag": tag,
                "last_attempt_time": 0.0,
                "retry_after": 0.0,
            })
            # Invariant: If an expired message (date < today) is injected or recovered, invalidate latch
            today_tag = self.get_today_date_tag()
            if msg_date_tag < today_tag and self.history.get("last_reconciled_date") == today_tag:
                self.history["last_reconciled_date"] = ""
            self._save_history()

    def reconcile_expired_messages(self, now_dt: datetime | None = None, force: bool = False) -> int:
        """Reconcile historical dispatched webhook messages with check throttle, one-delete-per-call,
        and daily completion latch.

        Invariants:
        1. Daily Completion Latch: If today's expired messages have already been fully cleared
           (last_reconciled_date == today_tag), O(1) in-memory early return with zero disk/network I/O.
        2. Check Throttle: Evaluated at most once every check_interval_seconds (5.0s) via time.monotonic() unless force=True.
        3. Earliest Time: No-op before 07:00 Asia/Taipei business time.
        4. One-Delete-Per-Call: Dispatches at most 1 DELETE request per invocation, bounding single-step latency.
        5. Cooldown: Retried messages obey at least 60s monotonic cooldown or Discord Retry-After.
        6. Completion Condition: Once all expired messages (date < today_tag) are cleared,
           records last_reconciled_date = today_tag to disarm reconciliation until tomorrow 07:00.
        """
        b_dt = resolve_business_dt(now_dt)
        today_tag = b_dt.strftime("%Y-%m-%d")

        # 1. Daily Completion Latch: O(1) in-memory early return if already fully cleared today
        if not force and self.history.get("last_reconciled_date") == today_tag:
            return 0

        # 2. Check Throttle: monotonic time prevents NTP / system clock skew
        monotonic_ts = time.monotonic()
        if not force and monotonic_ts < self._next_reconcile_check_ts:
            return 0

        self._next_reconcile_check_ts = monotonic_ts + self.check_interval_seconds

        # 3. Earliest Time Gate (07:00 Asia/Taipei)
        if b_dt.time() < dtime(EARLIEST_RECONCILE_HOUR, EARLIEST_RECONCILE_MINUTE):
            return 0

        dispatched = self.history.get("dispatched_messages", [])
        expired_items = [
            m for m in dispatched
            if str(m.get("date", "")) and str(m.get("date", "")) < today_tag
        ]

        # If no expired messages remain, mark today as fully reconciled and latch
        if not expired_items:
            if self.history.get("last_reconciled_date") != today_tag:
                self.history["last_reconciled_date"] = today_tag
                self._save_history()
                logging.info("✨ [DailyPipelineNotifier] 今日 (07:00) 歷史過期訊息已全數清空，今日不再重複巡檢。")
            return 0

        # 4. Process at most ONE expired item that is not in cooldown
        for item in expired_items:
            last_attempt = float(item.get("last_attempt_time", 0.0))
            cooldown = max(DEFAULT_RECONCILE_COOLDOWN_SECONDS, float(item.get("retry_after", 0.0)))
            if (monotonic_ts - last_attempt) < cooldown:
                continue

            msg_id = str(item.get("id", "")).strip()
            if not msg_id:
                self._evict_message_id(msg_id)
                self._check_and_latch_completion(today_tag)
                return 1

            del_res = self.notification_port.delete_message(msg_id)
            if del_res.success:
                self._evict_message_id(msg_id)
                logging.info(
                    "🧹 [DailyPipelineNotifier] 歷史過期訊息 %s 已成功自 Discord 刪除並自追蹤清單移除 (狀態碼: %s)。",
                    msg_id,
                    del_res.status_code,
                )
                self._check_and_latch_completion(today_tag)
                return 1
            else:
                self._record_delete_failure(msg_id, monotonic_ts, del_res.retry_after_seconds)
                logging.warning(
                    "⚠️ [DailyPipelineNotifier] 歷史訊息 %s 刪除失敗 (狀態碼: %s, 錯誤: %s)，將於 %.1f 秒後重試。",
                    msg_id,
                    del_res.status_code,
                    del_res.error,
                    max(DEFAULT_RECONCILE_COOLDOWN_SECONDS, del_res.retry_after_seconds),
                )
                return 0

        return 0

    def _check_and_latch_completion(self, today_tag: str) -> None:
        """If no expired messages remain after eviction, latch last_reconciled_date."""
        dispatched = self.history.get("dispatched_messages", [])
        has_remaining_expired = any(
            str(m.get("date", "")) and str(m.get("date", "")) < today_tag
            for m in dispatched
        )
        if not has_remaining_expired:
            self.history["last_reconciled_date"] = today_tag
            self._save_history()
            logging.info("✨ [DailyPipelineNotifier] 歷史過期訊息已全數清空，已設定 last_reconciled_date = %s，今日不再巡檢。", today_tag)

    def _evict_message_id(self, message_id: str) -> None:
        self.history["dispatched_messages"] = [
            m for m in self.history.get("dispatched_messages", []) if m.get("id") != message_id
        ]
        self._save_history()

    def _record_delete_failure(self, message_id: str, attempt_time: float, retry_after: float) -> None:
        for m in self.history.get("dispatched_messages", []):
            if m.get("id") == message_id:
                m["last_attempt_time"] = attempt_time
                m["retry_after"] = float(retry_after or 0.0)
                break
        self._save_history()

    def on_tier1_subflow_completed(self, subflow_key: str = "bulletin_board", now_dt: datetime | None = None) -> Any:
        """Evaluate Tier 1 completion upon completing a subflow."""
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

        from runtime.notification_i18n import format_milestone1, format_subflow_status
        sf_statuses = []
        for sf in ["chest", "hero_draw", "blood_altar", "jewelry_workshop", "bulletin_board"]:
            done = self.daily_manager.is_subflow_completed(sf) if hasattr(self.daily_manager, "is_subflow_completed") else False
            sf_statuses.append(format_subflow_status(sf, done, language=self.language))

        title, description, fields, footer = format_milestone1(
            profile=self.profile,
            accepted_quests=accepted_quests,
            subflow_statuses=sf_statuses,
            language=self.language,
            now_dt=now_dt,
        )
        res = self.notification_port.notify_milestone(
            title=title,
            description=description,
            fields=fields,
            footer_text=footer,
            sync=True,
        )
        msg_id = getattr(res, "external_message_id", None)
        if msg_id:
            self.track_dispatched_message(msg_id, tag="milestone1", now_dt=now_dt)
        self.record_milestone_notified("milestone1", now_dt)
        logging.info("🔔 [DailyPipelineNotifier] 已發送 Milestone 1 (%s) 通知！", title)
        return res

    def on_bounty_quests_cleared(self, fallback_mode: str = "Tier 4 Loop (mix)", now_dt: datetime | None = None) -> Any:
        """Dispatch Milestone 2 when all bounty quests have been cleared and state machine switches to Tier 4."""
        if not self.is_milestone_eligible("milestone2", now_dt):
            return False

        from runtime.notification_i18n import format_milestone2
        title, description, fields, footer = format_milestone2(
            profile=self.profile,
            fallback_mode=fallback_mode,
            language=self.language,
            now_dt=now_dt,
        )
        res = self.notification_port.notify_milestone(
            title=title,
            description=description,
            fields=fields,
            footer_text=footer,
            sync=True,
        )
        msg_id = getattr(res, "external_message_id", None)
        if msg_id:
            self.track_dispatched_message(msg_id, tag="milestone2", now_dt=now_dt)
        self.record_milestone_notified("milestone2", now_dt)
        logging.info("🔔 [DailyPipelineNotifier] 已發送 Milestone 2 (%s) 通知！", title)
        return res

    def check_daily_claim_deadline(self, current_state: str = "UNKNOWN", now_dt: datetime | None = None) -> Any:
        """Periodically check if 08:05 reset deadline has been exceeded while Tier 1 claims remain incomplete."""
        if not self.daily_manager or not hasattr(self.daily_manager, "is_tier1_daily_claim_completed"):
            return False

        if self.daily_manager.is_tier1_daily_claim_completed():
            return False

        now_dt = resolve_business_dt(now_dt)
        reset_hour = getattr(self.daily_manager, "reset_hour", 8)
        reset_minute = getattr(self.daily_manager, "reset_minute", 5)
        reset_time = dtime(reset_hour, reset_minute)

        if now_dt.time() < reset_time:
            last_reset_dt = datetime.combine(now_dt.date() - timedelta(days=1), reset_time, tzinfo=now_dt.tzinfo)
        else:
            last_reset_dt = datetime.combine(now_dt.date(), reset_time, tzinfo=now_dt.tzinfo)

        deadline_dt = last_reset_dt + timedelta(minutes=self.deadline_minutes)

        if now_dt < deadline_dt:
            return False

        if not self.is_milestone_eligible("deadline_alarm", now_dt):
            return False

        pending_subflows = []
        if hasattr(self.daily_manager, "get_pending_tier1_subflows"):
            pending_subflows = self.daily_manager.get_pending_tier1_subflows()

        from runtime.notification_i18n import format_daily_claim_deadline_alarm
        title, reason, details, desc, footer = format_daily_claim_deadline_alarm(
            profile=self.profile,
            deadline_minutes=self.deadline_minutes,
            pending_subflows=pending_subflows,
            current_state=current_state,
            language=self.language,
            now_dt=now_dt,
        )
        res = self.notification_port.notify_alarm(
            code="DAILY_CLAIM_DEADLINE_EXCEEDED",
            title=title,
            reason=reason,
            details=details,
            description=desc,
            footer_text=footer,
            sync=True,
        )
        msg_id = getattr(res, "external_message_id", None)
        if msg_id:
            self.track_dispatched_message(msg_id, tag="deadline_alarm", now_dt=now_dt)
        self.record_milestone_notified("deadline_alarm", now_dt)
        logging.error("🚨 [DailyPipelineNotifier] 已觸發 DAILY_CLAIM_DEADLINE_EXCEEDED 警報通知！")
        return res


class NullDailyPipelineNotifier(DailyPipelineNotifier):
    """Null Object implementation guaranteeing non-None contract for GameStateMachine."""

    def __init__(self) -> None:
        self.notification_port = NullNotifier()
        self.daily_manager = None
        self.profile = "null"
        self.deadline_minutes = 30
        self.history = {}
        self.language = "zh-TW"

    def get_current_reset_tag(self, now_dt: datetime | None = None) -> str:
        return ""

    def get_today_date_tag(self, now_dt: datetime | None = None) -> str:
        return ""

    def is_milestone_eligible(self, milestone_key: str, now_dt: datetime | None = None) -> bool:
        return False

    def record_milestone_notified(self, milestone_key: str, now_dt: datetime | None = None) -> None:
        pass

    def track_dispatched_message(
        self,
        message_id: str,
        tag: str = "",
        now_dt: datetime | None = None,
    ) -> None:
        pass

    def reconcile_expired_messages(self, now_dt: datetime | None = None, force: bool = False) -> int:
        return 0

    def on_tier1_subflow_completed(self, subflow_key: str = "bulletin_board", now_dt: datetime | None = None) -> Any:
        return False

    def on_bounty_quests_cleared(self, fallback_mode: str = "Tier 4 Loop (mix)", now_dt: datetime | None = None) -> Any:
        return False

    def check_daily_claim_deadline(self, current_state: str = "UNKNOWN", now_dt: datetime | None = None) -> Any:
        return False
