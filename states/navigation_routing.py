"""Compatibility bridge from legacy machine fields to the pure navigation policy."""

from dataclasses import dataclass, replace
import logging
import time
from typing import Optional

from states.navigation_intent import (
    ActionDecision,
    ActionId,
    ActiveIntent,
    DecisionKind,
    IntentSnapshot,
    NavigationIntentPolicy,
    IntentId,
    ReasonCode,
)
from states.navigation_progress import (
    InFlightAction,
    NavigationProgress,
    ProgressStatus,
)
from utils.scene_snapshot import (
    DetectionProfileId,
    LobbyTabScope,
    SceneDetectionRequest,
    SceneSnapshot,
    TabId,
    next_navigation_frame_id,
    snapshot_from_scene_info,
)


@dataclass(frozen=True)
class NavigationRoutingContext:
    scene: SceneSnapshot
    intent_snapshot: IntentSnapshot
    active_intent: ActiveIntent
    decision: ActionDecision
    progress_status: ProgressStatus = ProgressStatus.IDLE
    observed_action: InFlightAction | None = None


def build_intent_snapshot(machine) -> IntentSnapshot:
    config = machine.config or {}
    return IntentSnapshot.from_legacy(
        need_diamond_collection=getattr(machine, "need_diamond_collection", False),
        enable_bread=getattr(machine, "enable_bread", False),
        need_bread_collection=getattr(machine, "need_bread_collection", False),
        primary_mode=config.get("type", "stage"),
        primary_target=config.get("name"),
        stamina_retreat_active=(
            getattr(machine, "stamina_retreat_start_time", None) is not None
        ),
    )


def resolve_expected_tab_from_machine(machine) -> Optional[TabId]:
    """從當前已提交之導航意圖、in-flight action 或 route decision 解析目標頁籤。

    Contract: docs/features/navigation/lobby_scene_contract.md
    """
    if machine is None:
        return None
    progress = getattr(machine, "navigation_progress", None)
    if isinstance(progress, NavigationProgress) and progress.in_flight:
        if progress.in_flight.expected_tab is not None:
            return progress.in_flight.expected_tab

    config = getattr(machine, "config", None) or {}
    config_type = config.get("type")

    # 檢查是否有正在進行的 activity intent (如首領或魔王討伐)
    active_intent = getattr(machine, "active_navigation_intent", None)
    if active_intent and getattr(active_intent, "intent_id", None) == IntentId.TOWN_SUBFLOW:
        payload = getattr(active_intent, "payload", {}) or {}
        subflow = payload.get("flow_type") or payload.get("subflow")
        if subflow == "lord_boss":
            return TabId.LORD
        if subflow == "demon_lord":
            return TabId.DEMON_LORD

    _CONFIG_TYPE_TO_TAB: dict[str, TabId] = {
        "stage": TabId.STAGE,
        "dungeon": TabId.DUNGEON,
        "domain": TabId.DOMAIN,
        "lord": TabId.LORD,
        "demon_lord": TabId.DEMON_LORD,
    }
    if config_type in _CONFIG_TYPE_TO_TAB:
        return _CONFIG_TYPE_TO_TAB[config_type]
    if config_type in {"mix", "daily"}:
        has_dg = False
        try:
            has_dg = machine.has_available_dungeon()
        except Exception:
            has_dg = False
        return TabId.DUNGEON if has_dg else TabId.STAGE

    return None


TAB_ID_TO_PROFILE: dict[TabId, DetectionProfileId] = {
    TabId.STAGE: DetectionProfileId.STAGE_SELECT,
    TabId.DUNGEON: DetectionProfileId.DUNGEON_SELECT,
    TabId.DOMAIN: DetectionProfileId.DOMAIN_SELECT,
    TabId.LORD: DetectionProfileId.LORD_SELECT,
    TabId.DEMON_LORD: DetectionProfileId.DEMON_LORD_SELECT,
}


def resolve_detection_request(machine) -> SceneDetectionRequest:
    """
    依據當前狀態機狀態產出感知請求 (SceneDetectionRequest)。
    已知目標時以 EXPECTED_TAB 限制頁籤感知為一對 active/inactive 模板；
    無明確目標或異常時回傳 FULL_RELOCALIZE。
    """
    if machine is None:
        return SceneDetectionRequest(
            profile=DetectionProfileId.UNKNOWN,
            expected_tab=None,
            tab_scope=LobbyTabScope.FULL_RELOCALIZE,
            reason="machine_none",
        )

    expected_tab = resolve_expected_tab_from_machine(machine)
    if expected_tab is None:
        return SceneDetectionRequest(
            profile=DetectionProfileId.UNKNOWN,
            expected_tab=None,
            tab_scope=LobbyTabScope.FULL_RELOCALIZE,
            reason="uncommitted_route",
        )

    profile = TAB_ID_TO_PROFILE.get(expected_tab, DetectionProfileId.LOBBY)
    return SceneDetectionRequest(
        profile=profile,
        expected_tab=expected_tab,
        tab_scope=LobbyTabScope.EXPECTED_TAB,
        reason="navigation_steady",
    )


def resolve_navigation_context(machine, scene_info) -> NavigationRoutingContext:
    start_template = (machine.config or {}).get("lobby_start_btn", "stages/start.png")
    now = _monotonic_now(machine)
    scene = snapshot_from_scene_info(
        scene_info,
        frame_id=next_navigation_frame_id(machine),
        captured_at=now,
        start_template=start_template,
    )
    intent_snapshot = build_intent_snapshot(machine)
    policy = NavigationIntentPolicy()
    candidate = getattr(machine, "navigation_progress", None)
    progress = candidate if isinstance(candidate, NavigationProgress) else None
    observed_action = progress.in_flight if progress is not None else None
    progress_status = (
        progress.observe(scene, now) if progress is not None else ProgressStatus.IDLE
    )
    recovery_intent = (
        progress.take_recovery_intent()
        if progress_status == ProgressStatus.DEFERRED
        else None
    )
    if recovery_intent is not None:
        machine.request_relaunch(
            f"collection_recovery_limit_{recovery_intent.value}"
        )
        active_intent = ActiveIntent(recovery_intent)
        machine.active_navigation_intent = active_intent
        return NavigationRoutingContext(
            scene,
            intent_snapshot,
            active_intent,
            ActionDecision.wait(),
            progress_status,
            observed_action,
        )
    if progress_status == ProgressStatus.WAITING:
        active_intent = ActiveIntent(progress.in_flight.intent_id)
        decision = ActionDecision.wait(ReasonCode.IN_FLIGHT_ACTION_WAITING)
        machine.active_navigation_intent = active_intent
        return NavigationRoutingContext(
            scene,
            intent_snapshot,
            active_intent,
            decision,
            progress_status,
            observed_action,
        )

    active_intent = _select_available_intent(policy, intent_snapshot, progress, now)
    machine.active_navigation_intent = active_intent
    decision = policy.resolve(scene, active_intent)
    if progress_status == ProgressStatus.TIMED_OUT and decision.kind != DecisionKind.WAIT:
        decision = replace(decision, reason=ReasonCode.ACTION_TIMEOUT_RETRY)
    return NavigationRoutingContext(
        scene,
        intent_snapshot,
        active_intent,
        decision,
        progress_status,
        observed_action,
    )


def _select_available_intent(policy, snapshot, progress, now):
    selected = policy.select_intent(snapshot)
    if progress is None or not progress.is_deferred(selected.intent_id, now):
        return selected
    if (
        selected.intent_id == IntentId.COLLECT_DIAMOND
        and snapshot.bread_pending
        and not progress.is_deferred(IntentId.COLLECT_BREAD, now)
    ):
        return ActiveIntent(IntentId.COLLECT_BREAD)
    return ActiveIntent(IntentId.PRIMARY_NAVIGATION, snapshot.primary_payload)


def _monotonic_now(machine):
    clock = getattr(machine, "__dict__", {}).get("clock")
    return clock.monotonic() if clock is not None else time.monotonic()


class NavigationDecisionExecutor:
    """Execute one shared policy decision through an existing Handler boundary."""

    def __init__(self, handler):
        self.handler = handler
        self.machine = handler.machine

    def execute(self, context, screen_img, rect, *, start_callback=None) -> bool:
        decision = context.decision
        action = context.observed_action
        if action is not None:
            now = _monotonic_now(self.machine)
            logging.info(
                "[IntentRouting] intent=%s scene=%s action=%s reason=%s "
                "progress=%s in_flight=%s expected=%s age=%.1fs "
                "deadline=%.3f attempt=%d",
                context.active_intent.intent_id.value,
                context.scene.scene.value,
                decision.action.value if decision.action else "none",
                decision.reason.value,
                context.progress_status.value,
                action.action_id.value,
                action.expected.value,
                max(0.0, now - action.issued_at),
                action.deadline,
                action.attempt,
            )
        else:
            logging.info(
                "[IntentRouting] intent=%s scene=%s action=%s reason=%s progress=%s",
                context.active_intent.intent_id.value,
                context.scene.scene.value,
                decision.action.value if decision.action else "none",
                decision.reason.value,
                context.progress_status.value,
            )
        if decision.kind == DecisionKind.WAIT:
            return True
        if decision.action == ActionId.CONTINUE_PRIMARY:
            return False
        if decision.action == ActionId.START_PRIMARY:
            if start_callback is not None:
                start_callback()
            else:
                self.machine.transition_to(self.machine.STATE_LOBBY)
            return True
        if decision.action in {ActionId.OPEN_DIAMOND, ActionId.HANDLE_DIAMOND}:
            self._begin_action(context)
            return self._delegate_collection(
                self.machine.STATE_DIAMOND_COLLECTION,
                screen_img,
                rect,
            )
        if decision.action in {ActionId.OPEN_BREAD, ActionId.HANDLE_BREAD}:
            self._begin_action(context)
            return self._delegate_collection(
                self.machine.STATE_BREAD_COLLECTION,
                screen_img,
                rect,
            )
        if decision.action == ActionId.DISMISS_OVERLAY:
            return self._dismiss_overlay(context, rect)
        return self._click_snapshot_element(context, rect)

    def _delegate_collection(self, target_state, screen_img, rect) -> bool:
        self.machine.transition_to(target_state)
        self.machine.handlers[target_state].handle(screen_img, rect)
        return True

    def _click_snapshot_element(self, context, rect) -> bool:
        element = context.decision.element
        match = context.scene.elements.get(element)
        if match is None:
            return True
        self.handler.mouse.click(
            rect["left"] + match.client_x,
            rect["top"] + match.client_y,
        )
        self._begin_action(context)
        return True

    def _dismiss_overlay(self, context, rect) -> bool:
        element = context.decision.element
        match = context.scene.elements.get(element)
        if match is None:
            return True
        self.handler.click_and_wait_until_gone(
            match.template_name,
            rect["left"] + match.client_x,
            rect["top"] + match.client_y,
            rect,
            threshold=0.75,
        )
        self._begin_action(context)
        return True

    def _begin_action(self, context):
        decision = context.decision
        candidate = getattr(self.machine, "navigation_progress", None)
        progress = candidate if isinstance(candidate, NavigationProgress) else None
        if (
            progress is None
            or decision.kind != DecisionKind.CLICK
            or decision.action is None
            or decision.expected is None
        ):
            return
        expected_tab = resolve_expected_tab_from_machine(self.machine)
        progress.begin(
            context.active_intent.intent_id,
            decision.action,
            decision.expected,
            context.scene.frame_id,
            _monotonic_now(self.machine),
            expected_tab=expected_tab,
        )
