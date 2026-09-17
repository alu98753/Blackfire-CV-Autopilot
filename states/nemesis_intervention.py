"""Bounded operator intervention lifecycle for nemesis encounters.

This module owns the intervention session only.  Pause ownership, game-side
flee actions, and notification transport remain with their existing owners.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Any


class InterventionOutcome(str, Enum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    TIMED_OUT = "TIMED_OUT"


class UserResumeDecision(str, Enum):
    """Decision returned to the runtime user-input boundary."""

    NO_INTERVENTION = "NO_INTERVENTION"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    BLOCKED_TIMEOUT = "BLOCKED_TIMEOUT"


@dataclass
class _Session:
    encounter_id: str
    flee_callback: Callable[[], Any] | None = None
    outcome: InterventionOutcome = InterventionOutcome.ACTIVE
    message_ids: list[str] = field(default_factory=list)
    timer: Any = None
    timeout_side_effects_complete: bool = False
    timeout_recovery_pending: bool = False
    timeout_recovery_in_progress: bool = False
    timeout_cleanup_message_ids: list[str] = field(default_factory=list)


class NemesisIntervention:
    """Coordinate one active nemesis intervention with exact-once resolution."""

    DEFAULT_NOTIFICATION_COUNT = 5
    DEFAULT_GRACE_PERIOD_SECONDS = 60.0

    def __init__(
        self,
        machine,
        notification_port=None,
        *,
        timer_factory: Callable[[float, Callable[[], None]], Any] | None = None,
    ):
        self.machine = machine
        self.notification_port = notification_port or getattr(machine, "notification_port", None)
        self._timer_factory = timer_factory or self._default_timer
        self._lock = threading.Lock()
        self._active: _Session | None = None

    @staticmethod
    def _default_timer(delay, callback):
        timer = threading.Timer(delay, callback)
        timer.daemon = True
        return timer

    @property
    def active(self) -> bool:
        with self._lock:
            return self._active is not None and self._active.outcome is InterventionOutcome.ACTIVE

    @property
    def outcome(self) -> InterventionOutcome | None:
        with self._lock:
            return self._active.outcome if self._active else None

    @property
    def tracked_message_ids(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(self._active.message_ids) if self._active else ()

    def start(
        self,
        encounter_id: str,
        flee_callback: Callable[[], Any],
        *,
        notification_count: int = DEFAULT_NOTIFICATION_COUNT,
        grace_period_seconds: float = DEFAULT_GRACE_PERIOD_SECONDS,
        notification_code: str = "NEMESIS_INTERVENTION",
        notification_title: str = "Nemesis detected",
        notification_reason: str = "Operator action required",
        notification_details: dict[str, Any] | None = None,
    ) -> bool:
        """Start one session; duplicate active starts are no-ops."""
        with self._lock:
            if self._active is not None and self._active.outcome is InterventionOutcome.ACTIVE:
                return False
            session = _Session(str(encounter_id), flee_callback=flee_callback)
            self._active = session

        # Pause is authoritative and happens before auxiliary notification IO.
        try:
            self.machine.pause()
        except Exception:
            logging.exception("[NemesisIntervention] authoritative pause failed")

        count = max(0, int(notification_count))
        for _ in range(count):
            self._send_alarm(
                session,
                notification_code,
                notification_title,
                notification_reason,
                notification_details,
            )

        try:
            timer = self._timer_factory(max(0.0, float(grace_period_seconds)), self._on_timeout)
            with self._lock:
                if self._active is session and session.outcome is InterventionOutcome.ACTIVE:
                    session.timer = timer
                else:
                    timer.cancel()
                    timer = None
            if timer is not None:
                timer.start()
        except Exception:
            logging.exception("[NemesisIntervention] failed to arm grace deadline")
            # A paused ACTIVE session must always converge through the same
            # terminal arbitration path when its deadline owner cannot start.
            self._on_timeout()
        return True

    def _send_alarm(self, session, code, title, reason, details):
        try:
            result = self.notification_port.notify_alarm(
                code, title, reason, details=details, sync=True
            ) if self.notification_port is not None else None
            message_id = getattr(result, "external_message_id", None)
            if not isinstance(message_id, str) or not message_id.strip():
                return
            with self._lock:
                if self._active is session and session.outcome is InterventionOutcome.ACTIVE:
                    session.message_ids.append(message_id)
                    return
            self._delete_best_effort(message_id)
        except Exception:
            logging.exception("[NemesisIntervention] notification send failed")

    def acknowledge(self) -> bool:
        """Atomically claim acknowledgement and delete every tracked alarm."""
        with self._lock:
            session = self._active
            if session is None or session.outcome is not InterventionOutcome.ACTIVE:
                return False
            session.outcome = InterventionOutcome.ACKNOWLEDGED
            timer = session.timer
            message_ids = list(session.message_ids)
            session.message_ids.clear()
        self._cancel_timer(timer)
        for message_id in message_ids:
            self._delete_best_effort(message_id)
        return True

    def request_user_resume(self) -> UserResumeDecision:
        """Claim ACK for a user resume, or block while timeout owns side effects.

        ``NO_INTERVENTION`` intentionally means the caller may preserve the
        normal manual-resume behavior.  The runtime never infers lifecycle
        meaning from a raw ``active`` flag.
        """
        with self._lock:
            session = self._active
            if session is None:
                return UserResumeDecision.NO_INTERVENTION
            if session.outcome is InterventionOutcome.TIMED_OUT:
                if not session.timeout_side_effects_complete:
                    return UserResumeDecision.BLOCKED_TIMEOUT
                return UserResumeDecision.NO_INTERVENTION
            if session.outcome is not InterventionOutcome.ACTIVE:
                return UserResumeDecision.NO_INTERVENTION
            session.outcome = InterventionOutcome.ACKNOWLEDGED
            timer = session.timer
            message_ids = list(session.message_ids)
            session.message_ids.clear()
        self._cancel_timer(timer)
        for message_id in message_ids:
            self._delete_best_effort(message_id)
        return UserResumeDecision.ACKNOWLEDGED

    def blocks_user_toggle(self) -> bool:
        """Return whether timeout-owned recovery currently owns the hotkey."""
        with self._lock:
            session = self._active
            return bool(
                session
                and session.outcome is InterventionOutcome.TIMED_OUT
                and not session.timeout_side_effects_complete
            )

    def has_pending_timeout_recovery(self) -> bool:
        """Expose only the bounded recovery handoff to the runtime loop."""
        with self._lock:
            session = self._active
            return bool(
                session
                and session.outcome is InterventionOutcome.TIMED_OUT
                and (
                    session.timeout_recovery_pending
                    or session.timeout_recovery_in_progress
                )
            )

    def run_pending_timeout_recovery(self) -> bool:
        """Run timeout-owned game recovery on the authoritative runtime path."""
        with self._lock:
            session = self._active
            if (
                session is None
                or session.outcome is not InterventionOutcome.TIMED_OUT
                or not session.timeout_recovery_pending
                or session.timeout_recovery_in_progress
            ):
                return False
            session.timeout_recovery_pending = False
            session.timeout_recovery_in_progress = True
            message_ids = list(session.timeout_cleanup_message_ids)

        try:
            # Release the existing action/capture pause gate in this same
            # execution path immediately before reusing the game-side flow.
            self.machine.resume(user_initiated=False)
            self._run_flee(session)
            for message_id in message_ids:
                self._delete_best_effort(message_id)
        finally:
            with self._lock:
                if self._active is session:
                    session.timeout_recovery_in_progress = False
                    session.timeout_side_effects_complete = True
        return True

    def _on_timeout(self):
        with self._lock:
            session = self._active
            if session is None or session.outcome is not InterventionOutcome.ACTIVE:
                return False
            session.outcome = InterventionOutcome.TIMED_OUT
            message_ids = list(session.message_ids)
            # The first successfully tracked alarm is the retained history record.
            session.message_ids[:] = message_ids[:1]
            session.timeout_cleanup_message_ids = message_ids[1:]
            session.timeout_recovery_pending = True
        return True

    def _run_flee(self, session):
        try:
            # The callback is the existing BattleHandler flee subflow.
            if session.flee_callback is not None:
                session.flee_callback()
        except Exception:
            logging.exception("[NemesisIntervention] nemesis flee failed after timeout claim")

    def _delete_best_effort(self, message_id: str):
        try:
            if self.notification_port is not None:
                self.notification_port.delete_message(message_id)
        except Exception:
            logging.exception("[NemesisIntervention] notification delete failed: %s", message_id)

    @staticmethod
    def _cancel_timer(timer):
        if timer is not None:
            try:
                timer.cancel()
            except Exception:
                logging.exception("[NemesisIntervention] timer cancellation failed")
