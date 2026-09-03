"""Lifecycle state for one observed battle.

The game state machine owns this object.  Handlers may identify a scene change,
but must not keep their own copy of the battle timeout clock.
"""

from dataclasses import dataclass


@dataclass
class BattleSession:
    """Track the bounded recovery window for exactly one battle session."""

    started_at: float | None = None
    entry_state: str | None = None

    @property
    def is_active(self) -> bool:
        return self.started_at is not None

    def begin(self, now: float, entry_state: str) -> None:
        self.started_at = now
        self.entry_state = entry_state

    def clear(self) -> None:
        self.started_at = None
        self.entry_state = None

    def elapsed_seconds(self, now: float) -> float:
        if self.started_at is None:
            return 0.0
        return max(0.0, now - self.started_at)

    def compensate_pause(self, pause_duration: float) -> None:
        if self.started_at is not None:
            self.started_at += pause_duration
