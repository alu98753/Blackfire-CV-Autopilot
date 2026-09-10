"""Shared precondition navigation for workflows whose destination is Town."""

import logging

from states.navigation_intent import (
    ActionDecision,
    ActionId,
    ActiveIntent,
    DecisionKind,
    IntentId,
    PostconditionId,
    ReasonCode,
)
from states.navigation_progress import NavigationProgress, ProgressStatus
from states.navigation_table import NavigationGoal, NavigationTable
from states.town_subflow_perception import TownSubflowPerception
from states.town_subflow_registry import TOWN_SUBFLOW_SPECS, spec_for
from utils.scene_snapshot import ElementId, SceneId, SceneSnapshot


TOWN_SUBFLOW_DEFER_SECONDS = 180


class TownSubflowPolicy:
    """Resolve one task-agnostic REACH_TOWN action from one observation."""

    def resolve(self, scene: SceneSnapshot, flow_key: str) -> ActionDecision:
        if scene.has(ElementId.CLOSE_OVERLAY):
            return ActionDecision.click(
                ReasonCode.TOWN_SUBFLOW_CLOSE_OVERLAY,
                ActionId.DISMISS_OVERLAY,
                PostconditionId.OVERLAY_CLOSED,
                ElementId.CLOSE_OVERLAY,
            )

        edge = NavigationTable().next_goal_edge(scene, NavigationGoal.REACH_TOWN)
        if edge is not None:
            return ActionDecision.click(
                edge.reason,
                edge.action,
                edge.postcondition,
                edge.required_element,
            )

        if scene.scene != SceneId.TOWN:
            return ActionDecision.wait()

        spec = spec_for(flow_key)
        if spec.dispatch_on_town:
            return ActionDecision.delegate(
                ReasonCode.TOWN_SUBFLOW_READY,
                ActionId.DISPATCH_TOWN_SUBFLOW,
                PostconditionId.PRIMARY_ROUTE_PROGRESS,
            )
        if not scene.has(ElementId.TOWN_SUBFLOW_ENTRY):
            return ActionDecision.wait()
        if spec.requires_red_dot:
            if scene.has(ElementId.TOWN_SUBFLOW_RED_DOT):
                return ActionDecision.delegate(
                    ReasonCode.TOWN_SUBFLOW_READY,
                    ActionId.DISPATCH_TOWN_SUBFLOW,
                    PostconditionId.PRIMARY_ROUTE_PROGRESS,
                )
            return ActionDecision.delegate(
                ReasonCode.TOWN_SUBFLOW_NO_RED_DOT,
                ActionId.COMPLETE_TOWN_SUBFLOW,
                PostconditionId.PRIMARY_ROUTE_PROGRESS,
            )
        return ActionDecision.delegate(
            ReasonCode.TOWN_SUBFLOW_READY,
            ActionId.DISPATCH_TOWN_SUBFLOW,
            PostconditionId.PRIMARY_ROUTE_PROGRESS,
        )


class TownSubflowPreconditionController:
    """Execute the shared route while preserving committed workflow owners."""

    def __init__(self, machine):
        self.machine = machine
        self.perception = TownSubflowPerception(machine)
        self.policy = TownSubflowPolicy()
        self._entry_wait_flow = None
        self._entry_wait_count = 0
        self._no_red_dot_flow = None
        self._no_red_dot_count = 0

    def _should_skip_handle(self, flow_key, progress) -> bool:
        if not flow_key or self._committed_workflow_owns_frame(flow_key):
            return True
        if isinstance(progress, NavigationProgress) and progress.in_flight:
            return progress.in_flight.intent_id != IntentId.TOWN_SUBFLOW
        return self._collection_pending()

    def handle(self, screen_img, rect) -> bool:
        flow_key = getattr(self.machine, "current_town_subflow", None)
        progress = getattr(self.machine, "navigation_progress", None)
        if self._should_skip_handle(flow_key, progress):
            return False

        scene = self.perception.observe(screen_img, flow_key)
        if scene.scene in {
            SceneId.BATTLE,
            SceneId.RESULT,
            SceneId.DUNGEON_EXPLORING,
        }:
            return False
        if isinstance(progress, NavigationProgress) and progress.in_flight:
            status = progress.observe(scene, scene.captured_at)
            if status == ProgressStatus.WAITING:
                return True
            if status == ProgressStatus.DEFERRED:
                self.machine.defer_current_town_subflow(
                    TOWN_SUBFLOW_DEFER_SECONDS
                )
                return True

        self.machine.active_navigation_intent = ActiveIntent(IntentId.TOWN_SUBFLOW)
        decision = self.policy.resolve(scene, flow_key)
        if decision.kind == DecisionKind.WAIT:
            self._reset_no_red_dot()
            if self._entry_wait_exhausted(scene, flow_key):
                self.machine.defer_current_town_subflow(
                    TOWN_SUBFLOW_DEFER_SECONDS
                )
                return True
            return scene.scene != SceneId.UNKNOWN
        self._reset_entry_wait()
        return self._execute_decision(decision, scene, flow_key, rect, progress)

    def _execute_decision(self, decision, scene, flow_key, rect, progress) -> bool:
        if decision.action == ActionId.DISPATCH_TOWN_SUBFLOW:
            self._reset_no_red_dot()
            self.machine.dispatch_current_town_subflow()
            return True
        if decision.action == ActionId.COMPLETE_TOWN_SUBFLOW:
            if self._no_red_dot_confirmed(scene, flow_key):
                self.machine.complete_current_town_subflow()
                return True
            return True
        self._reset_no_red_dot()
        if decision.action == ActionId.DEFER_TOWN_SUBFLOW:
            self.machine.defer_current_town_subflow(TOWN_SUBFLOW_DEFER_SECONDS)
            return True

        match = scene.elements.get(decision.element)
        if match is None:
            return True
        self.machine.mouse.click(
            rect["left"] + match.client_x,
            rect["top"] + match.client_y,
        )
        if isinstance(progress, NavigationProgress):
            progress.begin(
                IntentId.TOWN_SUBFLOW,
                decision.action,
                decision.expected,
                scene.frame_id,
                scene.captured_at,
            )
        logging.info(
            "[TownSubflowNavigation] flow=%s scene=%s action=%s reason=%s",
            flow_key,
            scene.scene.value,
            decision.action.value,
            decision.reason.value,
        )
        return True

    def _committed_workflow_owns_frame(self, flow_key):
        target_state = self.machine.state_for_town_subflow(flow_key)
        if target_state is not None and self.machine.current_state == target_state:
            return True
        return self.machine.current_state in {
            self.machine.STATE_BATTLE,
            self.machine.STATE_LOADING,
            self.machine.STATE_RESULT,
            self.machine.STATE_DUNGEON_EXPLORING,
            self.machine.STATE_POPUP_RECOVERY,
        }

    def _collection_pending(self):
        return bool(
            self.machine.need_diamond_collection
            or (self.machine.enable_bread and self.machine.need_bread_collection)
        )

    def _entry_wait_exhausted(self, scene, flow_key):
        """Bound Town-only entry discovery; UNKNOWN remains non-destructive."""
        if scene.scene != SceneId.TOWN:
            self._reset_entry_wait()
            return False
        if self._entry_wait_flow != flow_key:
            self._entry_wait_flow = flow_key
            self._entry_wait_count = 0
        self._entry_wait_count += 1
        settings = self.machine.navigation_progress.settings
        return self._entry_wait_count >= settings.town_entry_wait_max_observations

    def _reset_entry_wait(self):
        self._entry_wait_flow = None
        self._entry_wait_count = 0

    def _no_red_dot_confirmed(self, scene, flow_key):
        """Bound Town-only completion confirmation; requires consecutive observations."""
        if scene.scene != SceneId.TOWN or not scene.has(ElementId.TOWN_SUBFLOW_ENTRY):
            self._reset_no_red_dot()
            return False
        if self._no_red_dot_flow != flow_key:
            self._no_red_dot_flow = flow_key
            self._no_red_dot_count = 0
        self._no_red_dot_count += 1
        progress = getattr(self.machine, "navigation_progress", None)
        settings = getattr(progress, "settings", None)
        max_obs = getattr(settings, "town_no_red_dot_confirm_frames", 2)
        return self._no_red_dot_count >= max_obs

    def _reset_no_red_dot(self):
        self._no_red_dot_flow = None
        self._no_red_dot_count = 0
