"""Minimal runtime ports used by the greenfield-lite control loop."""

import time
from typing import Protocol, runtime_checkable


@runtime_checkable
class CapturePort(Protocol):
    def get_window_rect(self): ...

    def capture(self, rect): ...


@runtime_checkable
class InputPort(Protocol):
    def click(self, x, y): ...

    def drag(self, start_x, start_y, end_x, end_y): ...


@runtime_checkable
class ClockPort(Protocol):
    def monotonic(self) -> float: ...


@runtime_checkable
class ProcessPort(Protocol):
    def relaunch(self, machine, reason: str) -> bool: ...


class SystemClock:
    def monotonic(self) -> float:
        return time.monotonic()


class GameRelaunchProcessAdapter:
    """Keep process mutation behind the existing recovery subflow."""

    def relaunch(self, machine, reason: str) -> bool:
        from states.exceptions.subflows import GameRelaunchSubflow

        return GameRelaunchSubflow().execute(machine, reason=reason)
