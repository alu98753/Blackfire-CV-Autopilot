"""Pure navigation intent selection and decision policy."""

from dataclasses import dataclass
from enum import Enum

from utils.scene_snapshot import ElementId, SceneId, SceneSnapshot


class IntentId(str, Enum):
    COLLECT_DIAMOND = "collect_diamond"
    COLLECT_BREAD = "collect_bread"
    PRIMARY_NAVIGATION = "primary_navigation"


class DecisionKind(str, Enum):
    CLICK = "click"
    DELEGATE = "delegate"
    WAIT = "wait"


class ActionId(str, Enum):
    OPEN_DIAMOND = "open_diamond"
    RETURN_TOWN = "return_town"
    HANDLE_DIAMOND = "handle_diamond"
    ENTER_LOBBY = "enter_lobby"
    OPEN_BREAD = "open_bread"
    HANDLE_BREAD = "handle_bread"
    START_PRIMARY = "start_primary"
    CONTINUE_PRIMARY = "continue_primary"


class PostconditionId(str, Enum):
    DIAMOND_WINDOW = "diamond_window"
    TOWN = "town"
    DIAMOND_HANDLER_PROGRESS = "diamond_handler_progress"
    LOBBY = "lobby"
    BREAD_WINDOW = "bread_window"
    BREAD_HANDLER_PROGRESS = "bread_handler_progress"
    LOADING_OR_BATTLE = "loading_or_battle"
    PRIMARY_ROUTE_PROGRESS = "primary_route_progress"


class ReasonCode(str, Enum):
    DIAMOND_WINDOW_READY = "diamond_window_ready"
    DIAMOND_RETURN_TO_TOWN = "diamond_return_to_town"
    DIAMOND_ENTRY_READY = "diamond_entry_ready"
    BREAD_WINDOW_READY = "bread_window_ready"
    BREAD_ENTER_LOBBY = "bread_enter_lobby"
    BREAD_ENTRY_READY = "bread_entry_ready"
    PRIMARY_START_READY = "primary_start_ready"
    PRIMARY_ROUTE_DELEGATED = "primary_route_delegated"
    SCENE_EVIDENCE_INSUFFICIENT = "scene_evidence_insufficient"


@dataclass(frozen=True)
class PrimaryPayload:
    mode: str
    target: str | None = None


@dataclass(frozen=True)
class IntentSnapshot:
    diamond_pending: bool
    bread_pending: bool
    primary_payload: PrimaryPayload
    stamina_retreat_active: bool = False

    @classmethod
    def from_legacy(
        cls,
        *,
        need_diamond_collection: bool,
        enable_bread: bool,
        need_bread_collection: bool,
        primary_mode: str,
        primary_target: str | None = None,
        stamina_retreat_active: bool = False,
    ):
        return cls(
            diamond_pending=bool(need_diamond_collection),
            bread_pending=bool(enable_bread and need_bread_collection),
            primary_payload=PrimaryPayload(primary_mode, primary_target),
            stamina_retreat_active=bool(stamina_retreat_active),
        )


@dataclass(frozen=True)
class ActiveIntent:
    intent_id: IntentId
    primary_payload: PrimaryPayload | None = None


@dataclass(frozen=True)
class ActionDecision:
    kind: DecisionKind
    reason: ReasonCode
    action: ActionId | None = None
    expected: PostconditionId | None = None
    element: ElementId | None = None

    @classmethod
    def click(cls, reason, action, expected, element):
        return cls(DecisionKind.CLICK, reason, action, expected, element)

    @classmethod
    def delegate(cls, reason, action, expected):
        return cls(DecisionKind.DELEGATE, reason, action, expected)

    @classmethod
    def wait(cls):
        return cls(DecisionKind.WAIT, ReasonCode.SCENE_EVIDENCE_INSUFFICIENT)


class NavigationIntentPolicy:
    """Deterministically choose one intent and one action per observation."""

    @staticmethod
    def select_intent(snapshot: IntentSnapshot) -> ActiveIntent:
        if snapshot.diamond_pending:
            return ActiveIntent(IntentId.COLLECT_DIAMOND)
        if snapshot.bread_pending:
            return ActiveIntent(IntentId.COLLECT_BREAD)
        return ActiveIntent(IntentId.PRIMARY_NAVIGATION, snapshot.primary_payload)

    def resolve(self, scene: SceneSnapshot, intent: ActiveIntent) -> ActionDecision:
        if intent.intent_id == IntentId.COLLECT_DIAMOND:
            return self._resolve_diamond(scene)
        if intent.intent_id == IntentId.COLLECT_BREAD:
            return self._resolve_bread(scene)
        return self._resolve_primary(scene)

    @staticmethod
    def _resolve_diamond(scene: SceneSnapshot) -> ActionDecision:
        if scene.scene == SceneId.DIAMOND_WINDOW:
            return ActionDecision.delegate(
                ReasonCode.DIAMOND_WINDOW_READY,
                ActionId.HANDLE_DIAMOND,
                PostconditionId.DIAMOND_HANDLER_PROGRESS,
            )
        if scene.scene == SceneId.TOWN and scene.has(ElementId.DIAMOND_ENTRY):
            return ActionDecision.click(
                ReasonCode.DIAMOND_ENTRY_READY,
                ActionId.OPEN_DIAMOND,
                PostconditionId.DIAMOND_WINDOW,
                ElementId.DIAMOND_ENTRY,
            )
        if scene.scene == SceneId.LOBBY and scene.has(ElementId.GOBACK_TOWN):
            return ActionDecision.click(
                ReasonCode.DIAMOND_RETURN_TO_TOWN,
                ActionId.RETURN_TOWN,
                PostconditionId.TOWN,
                ElementId.GOBACK_TOWN,
            )
        return ActionDecision.wait()

    @staticmethod
    def _resolve_bread(scene: SceneSnapshot) -> ActionDecision:
        if scene.scene == SceneId.BREAD_WINDOW:
            return ActionDecision.delegate(
                ReasonCode.BREAD_WINDOW_READY,
                ActionId.HANDLE_BREAD,
                PostconditionId.BREAD_HANDLER_PROGRESS,
            )
        if scene.scene == SceneId.LOBBY and scene.has(ElementId.BREAD_ENTRY):
            return ActionDecision.click(
                ReasonCode.BREAD_ENTRY_READY,
                ActionId.OPEN_BREAD,
                PostconditionId.BREAD_WINDOW,
                ElementId.BREAD_ENTRY,
            )
        if scene.scene == SceneId.TOWN and scene.has(ElementId.DOOR):
            return ActionDecision.click(
                ReasonCode.BREAD_ENTER_LOBBY,
                ActionId.ENTER_LOBBY,
                PostconditionId.LOBBY,
                ElementId.DOOR,
            )
        return ActionDecision.wait()

    @staticmethod
    def _resolve_primary(scene: SceneSnapshot) -> ActionDecision:
        if scene.scene == SceneId.LOBBY and scene.has(ElementId.START):
            return ActionDecision.click(
                ReasonCode.PRIMARY_START_READY,
                ActionId.START_PRIMARY,
                PostconditionId.LOADING_OR_BATTLE,
                ElementId.START,
            )
        return ActionDecision.delegate(
            ReasonCode.PRIMARY_ROUTE_DELEGATED,
            ActionId.CONTINUE_PRIMARY,
            PostconditionId.PRIMARY_ROUTE_PROGRESS,
        )
