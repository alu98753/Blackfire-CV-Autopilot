"""Coordinator for daily pipeline milestone notifications and deadline alarms.

Follows Greenfield-lite architecture:
- Owned by GameStateMachine (similar to BattleSession / StaminaRetreatRecovery).
- Queries DailyManager for pure state facts without polluting daily_status.json.
- Tracks notification idempotency across restarts via injected NotificationHistoryPort.
- Dispatches milestones and alarms via NotificationPort with safe exception suppression.
- Delegates 07:00 Desired-State Reconciliation to DailyReconciliationService.
"""

from __future__ import annotations

import logging
from datetime import datetime, time as dtime, timedelta
from typing import Any

from ports.notification_history_port import (
    InMemoryNotificationHistoryStore,
    NotificationHistoryPort,
)
from ports.notification_port import NotificationPort, NullNotifier
from states.daily_reconciliation import (
    DailyReconciliationService,
    resolve_business_dt,
)


class DailyPipelineNotifier:
    """Coordinates Daily Pipeline Milestone 1, Milestone 2, and Deadline Alarm notifications."""

    def __init__(
        self,
        notification_port: NotificationPort | None = None,
        daily_manager: Any | None = None,
        profile: str | None = None,
        deadline_minutes: int = 30,
        history_store: NotificationHistoryPort | None = None,
        reconciliation_service: DailyReconciliationService | None = None,
        language: str | None = None,
        check_interval_seconds: float = 600.0,
    ) -> None:
        self.notification_port: NotificationPort = notification_port or NullNotifier()
        self.daily_manager = daily_manager
        self.profile = (profile or "native").strip()
        self.deadline_minutes = max(1, int(deadline_minutes))

        # Setup history store (pure dependency injection, default to in-memory store)
        self.history_store: NotificationHistoryPort = (
            history_store if history_store is not None else InMemoryNotificationHistoryStore()
        )

        # Setup reconciliation service
        if reconciliation_service is not None:
            self.reconciliation_service = reconciliation_service
        else:
            self.reconciliation_service = DailyReconciliationService(
                notification_port=self.notification_port,
                history_store=self.history_store,
                check_interval_seconds=check_interval_seconds,
            )

        if language is not None:
            from runtime.notification_i18n import normalize_language
            self.language = normalize_language(language)
        else:
            from config import get_notification_language
            self.language = get_notification_language(profile=self.profile)

    @property
    def history(self) -> dict[str, Any]:
        return self.history_store.load_history()

    def _save_history(self) -> None:
        self.history_store.save_history(self.history_store.load_history())

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
        return self.history_store.load_history().get(f"last_{milestone_key}_date") != current_tag

    def record_milestone_notified(self, milestone_key: str, now_dt: datetime | None = None) -> None:
        """Persist notified record to guarantee idempotency across process restarts."""
        current_tag = self.get_current_reset_tag(now_dt)
        history = self.history_store.load_history()
        history[f"last_{milestone_key}_date"] = current_tag
        self.history_store.save_history(history)

    def track_dispatched_message(
        self,
        message_id: str,
        tag: str = "",
        now_dt: datetime | None = None,
    ) -> None:
        """Track dispatched webhook message ID for future 07:00 reconciliation."""
        self.reconciliation_service.track_dispatched_message(message_id, tag=tag, now_dt=now_dt)

    @property
    def _next_reconcile_check_ts(self) -> float:
        return self.reconciliation_service._next_reconcile_check_ts

    @_next_reconcile_check_ts.setter
    def _next_reconcile_check_ts(self, val: float) -> None:
        self.reconciliation_service._next_reconcile_check_ts = val

    def reconcile_expired_messages(self, now_dt: datetime | None = None, force: bool = False) -> int:
        """Delegate message cleanup to DailyReconciliationService."""
        return self.reconciliation_service.reconcile_expired_messages(now_dt=now_dt, force=force)

    def evaluate_tier1_completion(
        self,
        subflow_key: str | datetime | None = None,
        now_dt: datetime | None = None,
    ) -> Any:
        """Evaluate Tier 1 completion at a lifecycle boundary and dispatch Milestone 1 if eligible.

        Domain Invariants:
        1. dm.is_tier1_daily_claim_completed() must hold (all enabled subflows completed).
        2. Must be milestone eligible for the current reset cycle (idempotency).
        """
        if isinstance(subflow_key, datetime) and now_dt is None:
            now_dt = subflow_key
            subflow_key = None

        if not self.daily_manager or not hasattr(self.daily_manager, "is_tier1_daily_claim_completed"):
            return False

        if not self.daily_manager.is_tier1_daily_claim_completed():
            return False

        if not self.is_milestone_eligible("milestone1", now_dt):
            return False

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
        if res.success and getattr(res, "external_message_id", None):
            msg_id = res.external_message_id
            self.track_dispatched_message(msg_id, tag="milestone1", now_dt=now_dt)
            self.record_milestone_notified("milestone1", now_dt)
            logging.info("🔔 [DailyPipelineNotifier] 已發送 Milestone 1 (%s) 通知！(msg_id: %s)", title, msg_id)
        else:
            logging.warning(
                "⚠️ [DailyPipelineNotifier] Milestone 1 發送失敗 (%s)，今日暫不標記完成，保留重試空間。",
                getattr(res, "error", "Unknown error"),
            )
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
        if res.success and getattr(res, "external_message_id", None):
            msg_id = res.external_message_id
            self.track_dispatched_message(msg_id, tag="milestone2", now_dt=now_dt)
            self.record_milestone_notified("milestone2", now_dt)
            logging.info("🔔 [DailyPipelineNotifier] 已發送 Milestone 2 (%s) 通知！(msg_id: %s)", title, msg_id)
        else:
            logging.warning(
                "⚠️ [DailyPipelineNotifier] Milestone 2 發送失敗 (%s)，今日暫不標記完成，保留重試空間。",
                getattr(res, "error", "Unknown error"),
            )
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
        if res.success:
            msg_id = getattr(res, "external_message_id", None)
            if msg_id:
                self.track_dispatched_message(msg_id, tag="deadline_alarm", now_dt=now_dt)
            self.record_milestone_notified("deadline_alarm", now_dt)
            logging.error("🚨 [DailyPipelineNotifier] 已觸發 DAILY_CLAIM_DEADLINE_EXCEEDED 警報通知！")
        else:
            logging.warning(
                "⚠️ [DailyPipelineNotifier] DAILY_CLAIM_DEADLINE_EXCEEDED 警報發送失敗 (%s)，今日暫不標記完成。",
                getattr(res, "error", "Unknown error"),
            )
        return res


class NullDailyPipelineNotifier(DailyPipelineNotifier):
    """Null Object implementation guaranteeing non-None contract for GameStateMachine."""

    def __init__(self) -> None:
        super().__init__(
            notification_port=NullNotifier(),
            daily_manager=None,
            history_store=InMemoryNotificationHistoryStore(),
            language="zh-TW",
        )

    def get_today_date_tag(self, now_dt: datetime | None = None) -> str:
        return ""

    def get_current_reset_tag(self, now_dt: datetime | None = None) -> str:
        return ""

    def evaluate_tier1_completion(self, subflow_key: str | datetime | None = None, now_dt: datetime | None = None) -> Any:
        return False

    def on_bounty_quests_cleared(self, fallback_mode: str = "Tier 4 Loop (mix)", now_dt: datetime | None = None) -> Any:
        return False

    def check_daily_claim_deadline(self, current_state: str = "UNKNOWN", now_dt: datetime | None = None) -> Any:
        return False

    def reconcile_expired_messages(self, now_dt: datetime | None = None, force: bool = False) -> int:
        return 0
