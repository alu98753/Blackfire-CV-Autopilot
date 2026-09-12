"""Application and domain orchestration service for 07:00 Desired-State webhook reconciliation."""

from __future__ import annotations

import logging
import time
from datetime import datetime, time as dtime, timedelta, timezone
from typing import Any

from ports.notification_history_port import (
    InMemoryNotificationHistoryStore,
    NotificationHistoryPort,
)
from ports.notification_port import NotificationPort, NullNotifier

DEFAULT_RECONCILE_CHECK_INTERVAL_SECONDS: float = 600.0  # 10 minutes
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


class DailyReconciliationService:
    """Orchestration service driving 07:00 historical message cleanup and desired-state convergence.

    All external side effects are strictly delegated to NotificationPort and NotificationHistoryPort.
    """

    def __init__(
        self,
        notification_port: NotificationPort | None = None,
        history_store: NotificationHistoryPort | None = None,
        check_interval_seconds: float = DEFAULT_RECONCILE_CHECK_INTERVAL_SECONDS,
    ) -> None:
        self.notification_port: NotificationPort = notification_port or NullNotifier()
        self.history_store: NotificationHistoryPort = history_store or InMemoryNotificationHistoryStore()
        self.check_interval_seconds = max(0.5, float(check_interval_seconds))
        self._next_reconcile_check_ts = 0.0

    def track_dispatched_message(
        self,
        message_id: str,
        tag: str = "",
        now_dt: datetime | None = None,
    ) -> None:
        """Track dispatched webhook message ID for future 07:00 reconciliation."""
        if not message_id:
            return

        b_dt = resolve_business_dt(now_dt)
        msg_date_tag = b_dt.strftime("%Y-%m-%d")
        history = self.history_store.load_history()

        if "dispatched_messages" not in history or not isinstance(history["dispatched_messages"], list):
            history["dispatched_messages"] = []

        existing = [m for m in history["dispatched_messages"] if m.get("id") == message_id]
        if not existing:
            history["dispatched_messages"].append({
                "id": str(message_id).strip(),
                "date": msg_date_tag,
                "tag": tag,
                "last_attempt_time": 0.0,
                "retry_after": 0.0,
            })
            # Invariant: If an expired message (date < today) is injected or recovered, invalidate latch
            today_tag = resolve_business_dt().strftime("%Y-%m-%d")
            if msg_date_tag < today_tag and history.get("last_reconciled_date") == today_tag:
                history["last_reconciled_date"] = ""
            self.history_store.save_history(history)

    def reconcile_expired_messages(self, now_dt: datetime | None = None, force: bool = False) -> int:
        """Reconcile historical dispatched webhook messages with check throttle, one-delete-per-call,
        and daily completion latch.
        """
        b_dt = resolve_business_dt(now_dt)
        today_tag = b_dt.strftime("%Y-%m-%d")

        history = self.history_store.load_history()

        # 1. Daily Completion Latch: O(1) in-memory early return if already fully cleared today
        if not force and history.get("last_reconciled_date") == today_tag:
            return 0

        # 2. Check Throttle: monotonic time prevents NTP / system clock skew
        monotonic_ts = time.monotonic()
        if not force and monotonic_ts < self._next_reconcile_check_ts:
            return 0

        self._next_reconcile_check_ts = monotonic_ts + self.check_interval_seconds

        # 3. Earliest Time Gate (07:00 Asia/Taipei)
        if b_dt.time() < dtime(EARLIEST_RECONCILE_HOUR, EARLIEST_RECONCILE_MINUTE):
            return 0

        dispatched = history.get("dispatched_messages", [])
        expired_items = [
            m for m in dispatched
            if str(m.get("date", "")) and str(m.get("date", "")) < today_tag
        ]

        # If no expired messages remain, mark today as fully reconciled and latch
        if not expired_items:
            if history.get("last_reconciled_date") != today_tag:
                history["last_reconciled_date"] = today_tag
                self.history_store.save_history(history)
                logging.info("✨ [DailyReconciliationService] 今日 (07:00) 歷史過期訊息已全數清空，今日不再重複巡檢。")
            return 0

        # 4. Process at most ONE expired item that is not in cooldown
        for item in expired_items:
            last_attempt = float(item.get("last_attempt_time", 0.0))
            cooldown = max(DEFAULT_RECONCILE_COOLDOWN_SECONDS, float(item.get("retry_after", 0.0)))
            if (monotonic_ts - last_attempt) < cooldown:
                continue

            msg_id = str(item.get("id", "")).strip()
            if not msg_id:
                self._evict_message_id(history, msg_id)
                self._check_and_latch_completion(history, today_tag)
                return 1

            del_res = self.notification_port.delete_message(msg_id)
            if del_res.success:
                self._evict_message_id(history, msg_id)
                logging.info(
                    "🧹 [DailyReconciliationService] 歷史過期訊息 %s 已成功自 Discord 刪除並自追蹤清單移除 (狀態碼: %s)。",
                    msg_id,
                    del_res.status_code,
                )
                self._check_and_latch_completion(history, today_tag)
                return 1
            else:
                self._record_delete_failure(history, msg_id, monotonic_ts, del_res.retry_after_seconds)
                logging.warning(
                    "⚠️ [DailyReconciliationService] 歷史訊息 %s 刪除失敗 (狀態碼: %s, 錯誤: %s)，將於 %.1f 秒後重試。",
                    msg_id,
                    del_res.status_code,
                    del_res.error,
                    max(DEFAULT_RECONCILE_COOLDOWN_SECONDS, del_res.retry_after_seconds),
                )
                return 0

        return 0

    def _check_and_latch_completion(self, history: dict[str, Any], today_tag: str) -> None:
        """If no expired messages remain after eviction, latch last_reconciled_date."""
        dispatched = history.get("dispatched_messages", [])
        has_remaining_expired = any(
            str(m.get("date", "")) and str(m.get("date", "")) < today_tag
            for m in dispatched
        )
        if not has_remaining_expired:
            history["last_reconciled_date"] = today_tag
            self.history_store.save_history(history)
            logging.info("✨ [DailyReconciliationService] 歷史過期訊息已全數清空，已設定 last_reconciled_date = %s，今日不再巡檢。", today_tag)

    def _evict_message_id(self, history: dict[str, Any], message_id: str) -> None:
        history["dispatched_messages"] = [
            m for m in history.get("dispatched_messages", []) if m.get("id") != message_id
        ]
        self.history_store.save_history(history)

    def _record_delete_failure(self, history: dict[str, Any], message_id: str, attempt_time: float, retry_after: float) -> None:
        for m in history.get("dispatched_messages", []):
            if m.get("id") == message_id:
                m["last_attempt_time"] = attempt_time
                m["retry_after"] = float(retry_after or 0.0)
                break
        self.history_store.save_history(history)
