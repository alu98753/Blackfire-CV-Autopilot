"""Lifecycle state for one observed battle.

The game state machine owns this object.  Handlers may identify a scene change,
but must not keep their own copy of the battle timeout clock.
"""

import logging
from dataclasses import dataclass


@dataclass
class BattleSession:
    """Track the bounded recovery window for exactly one battle session."""

    started_at: float | None = None
    entry_state: str | None = None
    last_hp_signature: int | None = None
    last_diff: int = 0
    hp_stall_started_at: float | None = None
    restart_battle_attempts: int = 0

    @property
    def is_active(self) -> bool:
        return self.started_at is not None

    def begin(self, now: float, entry_state: str) -> None:
        self.started_at = now
        self.entry_state = entry_state
        self.last_hp_signature = None
        self.last_diff = 0
        self.hp_stall_started_at = None
        self.restart_battle_attempts = 0

    def clear(self) -> None:
        self.started_at = None
        self.entry_state = None
        self.last_hp_signature = None
        self.last_diff = 0
        self.hp_stall_started_at = None
        self.restart_battle_attempts = 0

    def elapsed_seconds(self, now: float) -> float:
        if self.started_at is None:
            return 0.0
        return max(0.0, now - self.started_at)

    def compensate_pause(self, pause_duration: float) -> None:
        if self.started_at is not None:
            self.started_at += pause_duration
        if self.hp_stall_started_at is not None:
            self.hp_stall_started_at += pause_duration

    def is_hp_stalled(self, current_signature: int, now: float, timeout_seconds: float = 30.0) -> bool:
        """Check if health bar signature has remained statically unchanged for >= timeout_seconds.
        
        Args:
            current_signature: Pixel count of red health bar in the ROI (-1 if invalid).
            now: Current monotonic timestamp.
            timeout_seconds: Bounded timeout in seconds to declare a stall.
        """
        if current_signature <= 0:
            # ROI not visible or invalid frame, do not stall on empty frame
            return False

        if self.last_hp_signature is None:
            self.last_hp_signature = current_signature
            self.last_diff = 0
            self.hp_stall_started_at = now
            return False

        # If pixel difference exceeds tolerance (e.g. at least 25 pixels change), progress is made
        diff = abs(current_signature - self.last_hp_signature)
        self.last_diff = diff
        stalled_duration = max(0.0, now - self.hp_stall_started_at) if self.hp_stall_started_at is not None else 0.0
        logging.debug(
            "[BattleStall] HP sig: %d (prev: %s, diff: %d, stalled: %.1fs/%.1fs)",
            current_signature,
            str(self.last_hp_signature),
            diff,
            stalled_duration,
            timeout_seconds,
        )

        if diff >= 25:
            self.last_hp_signature = current_signature
            self.hp_stall_started_at = now
            return False

        # HP has not changed significantly
        if self.hp_stall_started_at is None:
            self.hp_stall_started_at = now
            return False

        return stalled_duration >= timeout_seconds

    def reset_after_restart(self, now: float) -> None:
        """Reset battle clock and health stall tracking after in-battle restart."""
        self.started_at = now
        self.last_hp_signature = None
        self.last_diff = 0
        self.hp_stall_started_at = None
        self.restart_battle_attempts += 1
