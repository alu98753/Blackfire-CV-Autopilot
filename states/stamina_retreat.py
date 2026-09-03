"""Bounded, observable recovery for a confirmed insufficient-stamina overlay."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
import logging
import os
import time

from config import GAME_CONFIGS


class StaminaRetreatPhase(str, Enum):
    IDLE = "idle"
    DISMISS_OVERLAY = "dismiss_overlay"
    WAIT_OVERLAY_DISMISS = "wait_overlay_dismiss"
    QUIT = "quit"
    WAIT_QUIT = "wait_quit"
    RETURN_TOWN = "return_town"
    WAIT_RETURN_TOWN = "wait_return_town"


@dataclass(frozen=True)
class StaminaRetreatSettings:
    dismiss_max_attempts: int
    quit_max_attempts: int
    return_town_max_attempts: int

    @classmethod
    def from_mapping(cls, values):
        return cls(
            dismiss_max_attempts=int(values["dismiss_max_attempts"]),
            quit_max_attempts=int(values["quit_max_attempts"]),
            return_town_max_attempts=int(values["return_town_max_attempts"]),
        )


@dataclass(frozen=True)
class StaminaRetreatObservation:
    overlay_template: str | None = None
    dismiss_template: str | None = None
    dismiss_position: tuple | None = None
    quit_template: str | None = None
    quit_position: tuple | None = None
    return_position: tuple | None = None
    town_visible: bool = False


class StaminaRetreatRecovery:
    """Own the dismiss-to-bounded-quit-to-collect-only recovery sequence.

    ``observe`` uses the caller's current frame only. ``advance`` performs at
    most one click (or one state transition) and waits for a later frame to
    validate the corresponding postcondition.
    """

    OVERLAY_STYLES = (
        (
            "no_bread/no_bread.png",
            0.90,
            ("no_bread/cancel.png", "common/quit.png"),
        ),
        (
            "no_bread/no_bread2.png",
            0.85,
            ("common/confirm.png", "common/ok.png", "no_bread/cancel.png"),
        ),
    )
    QUIT_TEMPLATES = (
        "common/quit.png",
        "exit_battle.png",
        "domains/common/exit_to_lobby.png",
    )
    RETURN_TOWN_TEMPLATE = "goback_town.png"
    TOWN_TEMPLATE = "common/door.png"

    def __init__(self, settings: StaminaRetreatSettings):
        self.settings = settings
        self.phase = StaminaRetreatPhase.IDLE
        self.overlay_template = None
        self.dismiss_attempts = 0
        self.quit_attempts = 0
        self.return_town_attempts = 0
        self.interrupted_state = None

    @property
    def is_active(self) -> bool:
        return self.phase != StaminaRetreatPhase.IDLE

    def reset(self) -> None:
        self.phase = StaminaRetreatPhase.IDLE
        self.overlay_template = None
        self.dismiss_attempts = 0
        self.quit_attempts = 0
        self.return_town_attempts = 0
        self.interrupted_state = None

    def observe(self, machine, screen_img) -> StaminaRetreatObservation:
        overlay_template = None
        dismiss_candidates = ()
        for template, threshold, candidates in self.OVERLAY_STYLES:
            position = self._match(machine, screen_img, template, threshold)
            if position is not None:
                overlay_template = template
                dismiss_candidates = candidates
                break

        dismiss_template, dismiss_position = self._first_match(
            machine, screen_img, dismiss_candidates, 0.80
        )
        quit_template, quit_position = self._first_match(
            machine, screen_img, self.QUIT_TEMPLATES, 0.80
        )
        return_position = self._match(
            machine, screen_img, self.RETURN_TOWN_TEMPLATE, 0.80
        )
        town_visible = self._match(machine, screen_img, self.TOWN_TEMPLATE, 0.80) is not None
        return StaminaRetreatObservation(
            overlay_template=overlay_template,
            dismiss_template=dismiss_template,
            dismiss_position=dismiss_position,
            quit_template=quit_template,
            quit_position=quit_position,
            return_position=return_position,
            town_visible=town_visible,
        )

    def handle(self, machine, screen_img, rect) -> bool:
        observation = self.observe(machine, screen_img)
        if not self.is_active:
            if observation.overlay_template is None:
                return False
            self._start(machine, observation.overlay_template)
        return self._advance(machine, observation, rect)

    def _start(self, machine, overlay_template: str) -> None:
        self.phase = StaminaRetreatPhase.DISMISS_OVERLAY
        self.overlay_template = overlay_template
        self.interrupted_state = machine.current_state
        logging.warning(
            "[StaminaRetreat] confirmed overlay=%s while state=%s; starting bounded recovery.",
            overlay_template,
            self.interrupted_state,
        )

    def _advance(self, machine, observation, rect) -> bool:
        if self.phase == StaminaRetreatPhase.DISMISS_OVERLAY:
            return self._dismiss_overlay(machine, observation, rect)
        if self.phase == StaminaRetreatPhase.WAIT_OVERLAY_DISMISS:
            return self._verify_overlay_dismissed(machine, observation)
        if self.phase == StaminaRetreatPhase.QUIT:
            return self._quit_once(machine, observation, rect)
        if self.phase == StaminaRetreatPhase.WAIT_QUIT:
            return self._verify_quit(machine, observation)
        if self.phase == StaminaRetreatPhase.RETURN_TOWN:
            return self._return_to_town(machine, observation, rect)
        if self.phase == StaminaRetreatPhase.WAIT_RETURN_TOWN:
            return self._verify_return_to_town(machine, observation)
        return False

    def _dismiss_overlay(self, machine, observation, rect) -> bool:
        if observation.overlay_template is None:
            self.phase = StaminaRetreatPhase.QUIT
            return True
        if observation.dismiss_position is None:
            self.dismiss_attempts += 1
            return self._escalate_if_exhausted(
                machine,
                self.dismiss_attempts,
                self.settings.dismiss_max_attempts,
                "stamina_overlay_dismiss_unavailable",
            )
        self._click(machine, rect, observation.dismiss_position)
        self.dismiss_attempts += 1
        self.phase = StaminaRetreatPhase.WAIT_OVERLAY_DISMISS
        logging.info("[StaminaRetreat] dismiss action=%s attempt=%d", observation.dismiss_template, self.dismiss_attempts)
        return True

    def _verify_overlay_dismissed(self, machine, observation) -> bool:
        if observation.overlay_template is None:
            self.phase = StaminaRetreatPhase.QUIT
            return True
        if self.dismiss_attempts >= self.settings.dismiss_max_attempts:
            machine.request_relaunch("stamina_overlay_dismiss_timeout")
            return True
        self.phase = StaminaRetreatPhase.DISMISS_OVERLAY
        return True

    def _quit_once(self, machine, observation, rect) -> bool:
        if observation.overlay_template is not None:
            self.phase = StaminaRetreatPhase.DISMISS_OVERLAY
            return True
        if observation.quit_position is None or self.quit_attempts >= self.settings.quit_max_attempts:
            self.phase = StaminaRetreatPhase.RETURN_TOWN
            return True
        self._click(machine, rect, observation.quit_position)
        self.quit_attempts += 1
        self.phase = StaminaRetreatPhase.WAIT_QUIT
        logging.info("[StaminaRetreat] quit action=%s attempt=%d/%d", observation.quit_template, self.quit_attempts, self.settings.quit_max_attempts)
        return True

    def _verify_quit(self, machine, observation) -> bool:
        if observation.overlay_template is not None:
            self.phase = StaminaRetreatPhase.DISMISS_OVERLAY
        elif observation.quit_position is not None and self.quit_attempts < self.settings.quit_max_attempts:
            self.phase = StaminaRetreatPhase.QUIT
        else:
            self.phase = StaminaRetreatPhase.RETURN_TOWN
        return True

    def _return_to_town(self, machine, observation, rect) -> bool:
        if observation.town_visible:
            return self._enter_collect_only(machine)
        if observation.return_position is None:
            return self._enter_collect_only(machine)
        if self.return_town_attempts >= self.settings.return_town_max_attempts:
            machine.request_relaunch("stamina_return_town_timeout")
            return True
        self._click(machine, rect, observation.return_position)
        self.return_town_attempts += 1
        self.phase = StaminaRetreatPhase.WAIT_RETURN_TOWN
        logging.info("[StaminaRetreat] return-to-town attempt=%d/%d", self.return_town_attempts, self.settings.return_town_max_attempts)
        return True

    def _verify_return_to_town(self, machine, observation) -> bool:
        if observation.town_visible:
            return self._enter_collect_only(machine)
        if observation.return_position is not None:
            self.phase = StaminaRetreatPhase.RETURN_TOWN
            return True
        # The known exit action disappeared. CollectOnly owns safe town routing.
        return self._enter_collect_only(machine)

    def _enter_collect_only(self, machine) -> bool:
        if getattr(machine, "original_config", None) is None:
            machine.original_config = self._resume_config(machine)
        if getattr(machine, "stamina_retreat_start_time", None) is None:
            machine.stamina_retreat_start_time = time.time()
        machine.config = GAME_CONFIGS["collect_only"].copy()
        machine.transition_to(machine.STATE_COLLECT_ONLY)
        logging.warning("[StaminaRetreat] recovery complete; deferred work will resume from COLLECT_ONLY.")
        self.reset()
        return True

    def _resume_config(self, machine):
        if (
            self.interrupted_state == getattr(machine, "STATE_DEMON_LORDS", None)
            and getattr(machine, "primary_config", None)
        ):
            # Do not resume a stale Demon Lord modal; restore Daily scheduling so
            # the still-available Demon Lord is selected again after retreat.
            return deepcopy(machine.primary_config)
        return deepcopy(machine.config)

    @staticmethod
    def _click(machine, rect, position) -> None:
        machine.mouse.click(rect["left"] + position[0], rect["top"] + position[1])

    @staticmethod
    def _match(machine, screen_img, template, threshold):
        if not os.path.exists(os.path.join("templates", template)):
            return None
        position, _ = machine.matcher.match(screen_img, template, threshold=threshold)
        return position

    def _first_match(self, machine, screen_img, templates, threshold):
        for template in templates:
            position = self._match(machine, screen_img, template, threshold)
            if position is not None:
                return template, position
        return None, None

    @staticmethod
    def _escalate_if_exhausted(machine, attempts, limit, reason):
        if attempts >= limit:
            machine.request_relaunch(reason)
        return True
