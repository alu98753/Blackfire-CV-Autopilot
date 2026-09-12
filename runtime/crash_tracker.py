"""Sliding-window crash loop detector and recovery stabilization tracker."""

from __future__ import annotations

import logging
import time

ACTIVE_RECOVERY_STATES = frozenset({"NAVIGATING", "BATTLE", "COLLECT_ONLY"})


def is_stabilized_active_state(state: object) -> bool:
    """Return True if child state indicates healthy active progress (not unknown/recovery)."""
    if not isinstance(state, str):
        return False
    normalized = state.strip().upper()
    return normalized in ACTIVE_RECOVERY_STATES or (
        normalized not in {"UNKNOWN", "POPUP_RECOVERY"} and "RECOVERY" not in normalized
    )


class CrashLoopTracker:
    """Tracks unexpected process terminations within a sliding time window."""

    def __init__(
        self,
        max_restarts: int = 5,
        relaunch_buffer_seconds: float = 30.0,
        watchdog_timeout: float = 90.0,
    ) -> None:
        self.max_restarts = max(1, int(max_restarts))
        self.relaunch_buffer = max(0.0, float(relaunch_buffer_seconds))
        self.watchdog_timeout = max(1.0, float(watchdog_timeout))
        self.t_relaunch = self.watchdog_timeout + self.relaunch_buffer
        self.t_window = self.t_relaunch * self.max_restarts

        self.restart_timestamps: list[float] = []
        self.restart_count: int = 0
        self.last_alarm_time: float = 0.0

    def prune(self, now: float) -> None:
        """Remove timestamps outside the observation window."""
        cutoff = now - self.t_window
        self.restart_timestamps = [t for t in self.restart_timestamps if t >= cutoff]

    def record_failure(self, now: float | None = None) -> bool:
        """Record an unexpected process failure. Returns True if crash loop limit is exceeded."""
        now = time.time() if now is None else now
        self.restart_count += 1
        self.restart_timestamps.append(now)
        self.prune(now)

        if len(self.restart_timestamps) >= self.max_restarts:
            if now - self.last_alarm_time >= self.t_relaunch:
                self.last_alarm_time = now
                return True
        return False

    def record_clean_restart(self) -> None:
        """Scheduled maintenance or deliberate manual restart resets consecutive count."""
        self.restart_count = 0

    def check_stabilized(self, uptime: float, state: object) -> bool:
        """Reset failures when child process maintains an active state for >= t_relaunch."""
        if uptime >= self.t_relaunch and is_stabilized_active_state(state):
            if self.restart_timestamps or self.restart_count > 0:
                logging.info(
                    "[CrashTracker] Child process stabilized (uptime >= %.0fs, state=%s); reset restart counter.",
                    self.t_relaunch,
                    state,
                )
                self.reset()
                return True
        return False

    def reset(self) -> None:
        """Clear recorded failures and reset restart count."""
        self.restart_timestamps.clear()
        self.restart_count = 0
