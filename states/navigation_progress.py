"""Bounded progress tracking for navigation and collection actions."""

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from states.navigation_intent import ActionId, IntentId, PostconditionId
from utils.scene_snapshot import SceneId, SceneSnapshot


class CollectionOutcome(str, Enum):
    SUCCESS = "success"
    COOLDOWN = "cooldown"
    DEFERRED = "deferred"


class ProgressStatus(str, Enum):
    IDLE = "idle"
    WAITING = "waiting"
    PROGRESSED = "progressed"
    TIMED_OUT = "timed_out"
    DEFERRED = "deferred"


@dataclass(frozen=True)
class NavigationProgressSettings:
    action_timeout_seconds: float
    action_max_attempts: int
    collection_backoff_seconds: float

    @classmethod
    def from_mapping(cls, values):
        return cls(
            action_timeout_seconds=float(values["action_timeout_seconds"]),
            action_max_attempts=int(values["action_max_attempts"]),
            collection_backoff_seconds=float(values["collection_backoff_seconds"]),
        )


@dataclass(frozen=True)
class InFlightAction:
    intent_id: IntentId
    action_id: ActionId
    expected: PostconditionId
    source_frame_id: int
    issued_at: float
    deadline: float
    attempt: int


class NavigationProgress:
    """Own one committed action and bounded retry state per intent."""

    COLLECTION_INTENTS = frozenset(
        {IntentId.COLLECT_DIAMOND, IntentId.COLLECT_BREAD}
    )

    def __init__(self, settings: NavigationProgressSettings):
        self.settings = settings
        self.in_flight: InFlightAction | None = None
        self._failure_counts = {}
        self._deferred_until = {}
        self._outcomes = {}

    @property
    def deferred_until(self):
        return MappingProxyType(dict(self._deferred_until))

    @property
    def outcomes(self):
        return MappingProxyType(dict(self._outcomes))

    def begin(self, intent_id, action_id, expected, frame_id, now):
        failures = self._failure_counts.get(intent_id, 0)
        self.in_flight = InFlightAction(
            intent_id=intent_id,
            action_id=action_id,
            expected=expected,
            source_frame_id=frame_id,
            issued_at=now,
            deadline=now + self.settings.action_timeout_seconds,
            attempt=failures + 1,
        )
        return self.in_flight

    def observe(self, scene: SceneSnapshot, now: float) -> ProgressStatus:
        action = self.in_flight
        if action is None:
            return ProgressStatus.IDLE
        if scene.frame_id <= action.source_frame_id:
            return ProgressStatus.WAITING
        if self._postcondition_met(action.expected, scene):
            self.in_flight = None
            self._failure_counts.pop(action.intent_id, None)
            return ProgressStatus.PROGRESSED
        if now < action.deadline:
            return ProgressStatus.WAITING

        self.in_flight = None
        failures = self._failure_counts.get(action.intent_id, 0) + 1
        self._failure_counts[action.intent_id] = failures
        if (
            action.intent_id in self.COLLECTION_INTENTS
            and failures >= self.settings.action_max_attempts
        ):
            self.defer(action.intent_id, now)
            return ProgressStatus.DEFERRED
        return ProgressStatus.TIMED_OUT

    def complete(self, intent_id: IntentId, outcome: CollectionOutcome):
        if self.in_flight and self.in_flight.intent_id == intent_id:
            self.in_flight = None
        self._failure_counts.pop(intent_id, None)
        self._deferred_until.pop(intent_id, None)
        self._outcomes[intent_id] = outcome

    def clear(self, intent_id: IntentId | None = None):
        if self.in_flight and (
            intent_id is None or self.in_flight.intent_id == intent_id
        ):
            self.in_flight = None

    def defer(self, intent_id: IntentId, now: float):
        if self.in_flight and self.in_flight.intent_id == intent_id:
            self.in_flight = None
        self._failure_counts.pop(intent_id, None)
        self._deferred_until[intent_id] = (
            now + self.settings.collection_backoff_seconds
        )
        self._outcomes[intent_id] = CollectionOutcome.DEFERRED

    def is_deferred(self, intent_id: IntentId, now: float) -> bool:
        retry_at = self._deferred_until.get(intent_id)
        if retry_at is None:
            return False
        if now < retry_at:
            return True
        self._deferred_until.pop(intent_id, None)
        return False

    @staticmethod
    def _postcondition_met(expected, scene):
        if expected == PostconditionId.DIAMOND_WINDOW:
            return scene.scene == SceneId.DIAMOND_WINDOW
        if expected == PostconditionId.BREAD_WINDOW:
            return scene.scene == SceneId.BREAD_WINDOW
        if expected == PostconditionId.TOWN:
            return scene.scene == SceneId.TOWN
        if expected == PostconditionId.LOBBY:
            return scene.scene == SceneId.LOBBY
        if expected == PostconditionId.LOADING_OR_BATTLE:
            return scene.scene in {SceneId.LOADING, SceneId.BATTLE}
        if expected == PostconditionId.OVERLAY_CLOSED:
            from utils.scene_snapshot import ElementId

            return not scene.has(ElementId.CLOSE_OVERLAY)
        return False
